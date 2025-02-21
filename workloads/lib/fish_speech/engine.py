import torch
import torchaudio
from typing import Optional, Tuple
from contextlib import nullcontext
from tqdm import tqdm
import soundfile as sf
import logging

from workloads.lib.fish_speech.modules.firefly import FireflyArchitecture, DownsampleFiniteScalarQuantize, \
    ConvNeXtEncoder, HiFiGANGenerator, LogMelSpectrogram
from workloads.lib.fish_speech.conversation import Conversation, Message, TextPart, VQPart
from workloads.lib.fish_speech.clean import clean_text
from workloads.lib.fish_speech.modules.autoregression import BaseTransformer, DualARTransformer
from workloads.lib.fish_speech.modules.tokenizer import IM_END_TOKEN


def load_model_weights(model, checkpoint_path, device="cuda"):
    state_dict = torch.load(
        checkpoint_path, map_location=device, mmap=True, weights_only=True
    )

    if "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    if any("generator" in k for k in state_dict):
        state_dict = {
            k.replace("generator.", ""): v
            for k, v in state_dict.items()
            if "generator." in k
        }

    model.load_state_dict(state_dict, strict=False, assign=True)
    model.eval()
    model.to(device)

    return model


def encode_tokens(
        tokenizer,
        string,
        device="cuda",
        prompt_tokens=None,
        num_codebooks=4,
):
    string = clean_text(string)

    messages = []
    messages.append(
        Message(
            role="user",
            parts=[TextPart(text=string)],
            cal_loss=False,
        )
    )

    if prompt_tokens is not None:
        if prompt_tokens.ndim == 3:
            assert (
                    prompt_tokens.shape[0] == 1
            ), "3D prompt tokens should have shape (1, num_codebooks, seq_len)"
            prompt_tokens = prompt_tokens[0]

        assert prompt_tokens.ndim == 2, "Prompt tokens should be 2D tensor"

        if prompt_tokens.shape[0] > num_codebooks:
            logger.warning(
                f"Prompt tokens shape {prompt_tokens.shape} is larger than num_codebooks {num_codebooks}, getting first {num_codebooks} codebooks"
            )
            prompt_tokens = prompt_tokens[:num_codebooks]

        vq_part = VQPart(codes=prompt_tokens.to(device))

        messages.append(
            Message(
                role="assistant",
                parts=[TextPart(text="<|voice|>"), vq_part],
                cal_loss=False,
            )
        )
    else:
        messages.append(
            Message(
                role="assistant",
                parts=[TextPart(text="<|voice|>")],
                cal_loss=False,
                add_im_end=False,
            )
        )

    conversation = Conversation(messages=messages)
    conversation.visualize(tokenizer)
    encoded = conversation.encode_for_inference(
        tokenizer=tokenizer,
        num_codebooks=num_codebooks,
    )

    return encoded.to(device)


def logits_to_probs(
        logits,
        previous_tokens: Optional[torch.Tensor] = None,
        temperature: torch.Tensor = 1.0,
        top_p: torch.Tensor = 1.0,
        repetition_penalty: torch.Tensor = 1.0,
) -> torch.Tensor:
    # Apply repetition penalty
    if previous_tokens is not None:
        previous_tokens = previous_tokens.long()
        score = torch.gather(logits, dim=0, index=previous_tokens)
        score = torch.where(
            score < 0, score * repetition_penalty, score / repetition_penalty
        )
        logits.scatter_(dim=0, index=previous_tokens, src=score)

    # Apply top-p sampling
    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
    cum_probs = torch.cumsum(torch.nn.functional.softmax(sorted_logits, dim=-1), dim=-1)
    sorted_indices_to_remove = cum_probs > top_p
    sorted_indices_to_remove[0] = False  # keep at least one option
    indices_to_remove = sorted_indices_to_remove.scatter(
        dim=0, index=sorted_indices, src=sorted_indices_to_remove
    )
    logits = logits.masked_fill(indices_to_remove, -float("Inf"))

    logits = logits / max(temperature, 1e-5)

    probs = torch.nn.functional.softmax(logits, dim=-1)
    return probs


def multinomial_sample_one_no_sync(
        probs_sort,
):  # Does multinomial sampling without a cuda synchronization
    q = torch.empty_like(probs_sort).exponential_(1)
    return torch.argmax(probs_sort / q, dim=-1, keepdim=True).to(dtype=torch.int)


def sample(
        logits,
        previous_tokens: Optional[torch.Tensor] = None,
        **sampling_kwargs,
) -> Tuple[torch.Tensor, torch.Tensor]:
    probs = logits_to_probs(
        logits=logits[0, -1], previous_tokens=previous_tokens, **sampling_kwargs
    )
    idx_next = multinomial_sample_one_no_sync(probs)
    return idx_next, probs


def decode_one_token_ar(
        model: DualARTransformer,
        x: torch.Tensor,
        input_pos: torch.Tensor,
        semantic_ids: list,
        previous_tokens: torch.Tensor = None,
        **sampling_kwargs,
) -> torch.Tensor:
    x = model.forward_generate(x, input_pos)

    sampling_kwargs_main = sampling_kwargs.copy()
    # sampling_kwargs_main["temperature"] = 0.1
    # sampling_kwargs_main["top_p"] = 0.1
    # sampling_kwargs_main["repetition_penalty"] = 1.0

    codebooks = [
        sample(
            x.logits,
            previous_tokens=(
                previous_tokens[0] if previous_tokens is not None else None
            ),  # Disable repetition penalty for the token codebook
            **sampling_kwargs_main,
        )[0]
    ]

    hidden_states = x.hidden_states

    # Cleanup the cache
    for layer in model.fast_layers:
        layer.attention.kv_cache.k_cache.fill_(0)
        layer.attention.kv_cache.v_cache.fill_(0)

    input_pos = torch.tensor([0], device=hidden_states.device, dtype=torch.long)
    model.forward_generate_fast(hidden_states, input_pos)
    a = codebooks[0] - model.tokenizer.semantic_begin_id
    a[a < 0] = 0
    hidden_states = model.fast_embeddings(a)
    codebooks.append(a)

    for codebook_idx in range(1, model.config.num_codebooks):
        input_pos = torch.tensor(
            [codebook_idx], device=hidden_states.device, dtype=torch.long
        )
        logits = model.forward_generate_fast(hidden_states, input_pos)
        a = sample(
            logits,
            previous_tokens=(
                previous_tokens[codebook_idx + 1]
                if previous_tokens is not None
                else None
            ),
            **sampling_kwargs,
        )[0]
        hidden_states = model.fast_embeddings(a)
        codebooks.append(a)

    codebooks = torch.stack(codebooks, dim=0)
    return codebooks


def decode_n_tokens_ar(
        model: DualARTransformer,
        cur_token: torch.Tensor,
        input_pos: torch.Tensor,
        num_new_tokens: int,
        semantic_ids: list,
        **sampling_kwargs,
):
    previous_tokens = torch.zeros(
        (model.config.num_codebooks + 1, model.config.max_seq_len),
        dtype=torch.int,
        device=cur_token.device,
    )

    for i in tqdm(range(num_new_tokens)):
        # We need to get windowed repeat penalty
        win_size = 16
        if i < win_size:
            window = previous_tokens[:, :win_size]
        else:
            window = previous_tokens[:, i - win_size: i]

        with (
            torch.backends.cuda.sdp_kernel(
                enable_flash=False, enable_mem_efficient=False, enable_math=True
            )
            if torch.cuda.is_available()
            else nullcontext()
        ):  # Actually better for Inductor to codegen attention here
            next_token = decode_one_token_ar(
                model=model,
                x=cur_token,
                input_pos=input_pos,
                previous_tokens=window,
                semantic_ids=semantic_ids,
                **sampling_kwargs,
            )

        input_pos += 1
        cur_token = next_token.view(1, model.config.num_codebooks + 1, -1)
        previous_tokens[:, i: i + 1] = next_token.view(
            model.config.num_codebooks + 1, -1
        )

        if cur_token[0, 0, -1] == model.tokenizer.get_token_id(IM_END_TOKEN):
            break

    return previous_tokens[:, : i + 1]


@torch.no_grad()
@torch.inference_mode()
def llm_generate(model: BaseTransformer, prompt: torch.Tensor, max_new_tokens: int,
                 **sampling_kwargs) -> torch.Tensor:
    """
    Takes a conditioning sequence (prompt) as input and continues to generate as many tokens as requested.
    """

    # create an empty tensor of the expected final shape and fill in the current tokens
    T = prompt.size(1)
    semantic_ids = [
        model.tokenizer.get_token_id(f"<|semantic:{i}|>") for i in range(1024)
    ]

    if max_new_tokens:
        if T + max_new_tokens > model.config.max_seq_len:
            max_new_tokens = model.config.max_seq_len - T
    else:
        T_new = model.config.max_seq_len
        max_new_tokens = T_new - T

    device, dtype = prompt.device, prompt.dtype

    codebook_dim = 1 + model.config.num_codebooks
    # create an empty tensor of the expected final shape and fill in the current tokens
    empty = torch.empty(
        (codebook_dim, model.config.max_seq_len), dtype=dtype, device=device
    )
    empty[:, :T] = prompt
    seq = empty
    input_pos = torch.arange(0, T, device=device)

    # Use non-accelerated version for now, to avoid compilation overhead
    next_token = decode_one_token_ar(
        model,
        prompt.view(1, codebook_dim, -1),
        input_pos,
        semantic_ids=semantic_ids,
        **sampling_kwargs,
    )
    seq[:, T: T + 1] = next_token

    input_pos = torch.tensor([T], device=device, dtype=torch.int)
    x = decode_n_tokens_ar(
        model,
        next_token.view(1, codebook_dim, -1),
        input_pos,
        max_new_tokens - 1,
        semantic_ids=semantic_ids,
        **sampling_kwargs,
    )
    # x = torch.cat(generated_tokens, dim=1)
    seq = seq[:, : T + 1 + x.size(1)]
    seq[:, T + 1:] = x

    return seq


class FishEngine:

    def __init__(self,
                 logger: logging.Logger = None,
                 vqgan_model_path="workloads/checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
                 ar_model_path="workloads/checkpoints/fish-speech-1.5/",
                 device="cuda"):
        self.logger = logger

        # 1️⃣ Define the Spectrogram Transform
        spec_transform = LogMelSpectrogram(
            sample_rate=44100,
            n_mels=160,
            n_fft=2048,
            hop_length=512,
            win_length=2048
        )

        # 2️⃣ Define the Backbone (Encoder)
        backbone = ConvNeXtEncoder(
            input_channels=160,
            depths=[3, 3, 9, 3],
            dims=[128, 256, 384, 512],
            drop_path_rate=0.2,
            kernel_size=7
        )

        # 3️⃣ Define the Head (Decoder / Generator)
        head = HiFiGANGenerator(
            hop_length=512,
            upsample_rates=[8, 8, 2, 2, 2],  # Strides
            upsample_kernel_sizes=[16, 16, 4, 4, 4],
            resblock_kernel_sizes=[3, 7, 11],
            resblock_dilation_sizes=[[1, 3, 5], [1, 3, 5], [1, 3, 5]],
            num_mels=512,
            upsample_initial_channel=512,
            pre_conv_kernel_size=13,
            post_conv_kernel_size=13
        )

        # 4️⃣ Define the Quantizer
        quantizer = DownsampleFiniteScalarQuantize(
            input_dim=512,
            n_groups=8,
            n_codebooks=1,
            levels=[8, 5, 5, 5],
            downsample_factor=[2, 2]
        )

        # 5️⃣ Initialize the FireflyArchitecture Model
        firefly = FireflyArchitecture(
            spec_transform=spec_transform,
            backbone=backbone,
            head=head,
            quantizer=quantizer
        )

        self.vq_gan = load_model_weights(firefly, vqgan_model_path, device=device)
        self.ar_model = BaseTransformer.from_pretrained(ar_model_path, load_weights=True).to(device)
        self.ar_model.eval()

        with torch.device(device):
            self.ar_model.setup_caches(
                max_batch_size=1,
                max_seq_len=self.ar_model.config.max_seq_len,
                dtype=next(self.ar_model.parameters()).dtype,
            )

        self.ar_model_inference_kwargs = {
            "temperature": torch.tensor(0.7, device=device, dtype=torch.float),
            "top_p": torch.tensor(0.7, device=device, dtype=torch.float),
            "repetition_penalty": torch.tensor(1.2, device=device, dtype=torch.float)
        }

        self.encoded_prompts = [
            Conversation(messages=[
                Message(
                    role="system",
                    parts=[TextPart(
                        text="Speak out the provided text.")],
                    cal_loss=False,
                )
            ]).encode_for_inference(
                tokenizer=self.ar_model.tokenizer,
                num_codebooks=self.ar_model.config.num_codebooks,
            ).to(device)
        ]
        self.device = device

    def _load_reference_audio_tensor(self, reference_audio_path: str) -> Tuple[torch.Tensor, torch.Tensor]:
        reference_audio, sample_rate = torchaudio.load(reference_audio_path)
        audio = torchaudio.functional.resample(reference_audio, sample_rate, self.vq_gan.spec_transform.sample_rate)
        audios = audio.unsqueeze(dim=0).to(self.device)
        audio_lengths = torch.tensor([audios.shape[2]], device=self.device, dtype=torch.long)
        return audios, audio_lengths

    def tts(self, text: str, reference_audio_path: str, reference_text: str, out_audio_filename: str):
        audios, audio_lengths = self._load_reference_audio_tensor(reference_audio_path)
        self.logger.info("Finished loading reference audio.")

        tokens, tokens_length = self.vq_gan.encode(audios, audio_lengths)
        self.logger.info(f"Finished encoding reference audio, tokens shape {tokens.shape}.")

        encoded_prompts = [t.clone() for t in self.encoded_prompts]
        encoded_prompts.append(
            encode_tokens(
                self.ar_model.tokenizer,
                string=reference_text,
                device=self.device,
                prompt_tokens=tokens,
                num_codebooks=self.ar_model.config.num_codebooks,
            )
        )
        encoded = [
            encode_tokens(
                self.ar_model.tokenizer,
                string=text,
                device=self.device,
                num_codebooks=self.ar_model.config.num_codebooks,
            )
        ]
        cat_encoded = torch.cat(encoded_prompts + encoded, dim=1)
        self.logger.info(f"Finished preparing LLM prompts input, shape {cat_encoded.shape}.")

        out_seq = llm_generate(model=self.ar_model, prompt=cat_encoded, max_new_tokens=0,
                               **self.ar_model_inference_kwargs)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        num_tokens_generated = out_seq.size(1) - cat_encoded.size(1)
        out_generated = out_seq[1:, cat_encoded.size(1):-1]

        self.logger.info(f"output tokens: {self.ar_model.tokenizer.decode(out_seq[0, cat_encoded.size(1):-1].tolist())}")
        assert (out_generated >= 0).all(), f"Negative code found"
        self.logger.info(
            f"Finished generate LLM outputs, shape {out_generated.shape}, num_tokens_generated {num_tokens_generated}.")

        output_audio, _ = self.vq_gan.decode(indices=out_generated[None],
                                             feature_lengths=torch.tensor([out_generated.shape[1]], device=self.device))

        output_audio_time = output_audio.shape[-1] / self.vq_gan.spec_transform.sample_rate
        self.logger.info(
            f"Finished decoding output audio, shape {output_audio.shape}, audio time {output_audio_time}.")

        output_audio_npy = output_audio[0, 0].float().cpu().detach().numpy()
        sf.write(out_audio_filename, output_audio_npy, self.vq_gan.spec_transform.sample_rate)
        self.logger.info(f"Finished writing audio into {out_audio_filename}.")
