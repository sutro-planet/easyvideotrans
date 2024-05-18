import os

import librosa
import numpy as np
import soundfile as sf
import torch
from tqdm import tqdm

from lib import dataset
from lib import nets
from lib import spec_utils
from lib import utils


AUDIO_REMOVE_DEVICE = "gpu"
AUDIO_REMOVE_FFT_SIZE = 2048
AUDIO_REMOVE_HOP_SIZE = 1024

class Separator(object):

    def __init__(self, model, device=None, batchsize=1, cropsize=256, postprocess=False):
        self.model = model
        self.offset = model.offset
        self.device = device
        self.batchsize = batchsize
        self.cropsize = cropsize
        self.postprocess = postprocess

    def _postprocess(self, X_spec, mask):
        if self.postprocess:
            mask_mag = np.abs(mask)
            mask_mag = spec_utils.merge_artifacts(mask_mag)
            mask = mask_mag * np.exp(1.j * np.angle(mask))

        X_mag = np.abs(X_spec)
        X_phase = np.angle(X_spec)

        y_spec = mask * X_mag * np.exp(1.j * X_phase)
        v_spec = (1 - mask) * X_mag * np.exp(1.j * X_phase)
        # y_spec = X_spec * mask
        # v_spec = X_spec - y_spec

        return y_spec, v_spec

    def _separate(self, X_spec_pad, roi_size):
        X_dataset = []
        patches = (X_spec_pad.shape[2] - 2 * self.offset) // roi_size
        for i in range(patches):
            start = i * roi_size
            X_spec_crop = X_spec_pad[:, :, start:start + self.cropsize]
            X_dataset.append(X_spec_crop)

        X_dataset = np.asarray(X_dataset)

        self.model.eval()
        with torch.no_grad():
            mask_list = []
            # To reduce the overhead, dataloader is not used.
            for i in tqdm(range(0, patches, self.batchsize)):
                X_batch = X_dataset[i: i + self.batchsize]
                X_batch = torch.from_numpy(X_batch).to(self.device)

                mask = self.model.predict_mask(torch.abs(X_batch))

                mask = mask.detach().cpu().numpy()
                mask = np.concatenate(mask, axis=2)
                mask_list.append(mask)

            mask = np.concatenate(mask_list, axis=2)

        return mask

    def separate(self, X_spec):
        n_frame = X_spec.shape[2]
        pad_l, pad_r, roi_size = dataset.make_padding(n_frame, self.cropsize, self.offset)
        X_spec_pad = np.pad(X_spec, ((0, 0), (0, 0), (pad_l, pad_r)), mode='constant')
        X_spec_pad /= np.abs(X_spec).max()

        mask = self._separate(X_spec_pad, roi_size)
        mask = mask[:, :, :n_frame]

        y_spec, v_spec = self._postprocess(X_spec, mask)

        return y_spec, v_spec

    def separate_tta(self, X_spec):
        n_frame = X_spec.shape[2]
        pad_l, pad_r, roi_size = dataset.make_padding(n_frame, self.cropsize, self.offset)
        X_spec_pad = np.pad(X_spec, ((0, 0), (0, 0), (pad_l, pad_r)), mode='constant')
        X_spec_pad /= X_spec_pad.max()

        mask = self._separate(X_spec_pad, roi_size)

        pad_l += roi_size // 2
        pad_r += roi_size // 2
        X_spec_pad = np.pad(X_spec, ((0, 0), (0, 0), (pad_l, pad_r)), mode='constant')
        X_spec_pad /= X_spec_pad.max()

        mask_tta = self._separate(X_spec_pad, roi_size)
        mask_tta = mask_tta[:, :, roi_size // 2:]
        mask = (mask[:, :, :n_frame] + mask_tta[:, :, :n_frame]) * 0.5

        y_spec, v_spec = self._postprocess(X_spec, mask)

        return y_spec, v_spec


def audio_remove(audioFileNameAndPath, voiceFileNameAndPath, instrumentFileNameAndPath, modelNameAndPath):
    if AUDIO_REMOVE_DEVICE == "cpu":
        device = torch.device('cpu')
    elif AUDIO_REMOVE_DEVICE == "gpu":
        device = device = torch.device('cuda:0')
    else:
        raise ValueError("Invalid device: {}".format(AUDIO_REMOVE_DEVICE))
    
    print("Loading model " + AUDIO_REMOVE_DEVICE)
    model = nets.CascadedNet(AUDIO_REMOVE_FFT_SIZE, AUDIO_REMOVE_HOP_SIZE, 32, 128)#模型参数
    model.load_state_dict(torch.load(modelNameAndPath, map_location='cpu'))
    model.to(device)
    print("Model loaded")

    print('loading wave source ' + audioFileNameAndPath)
    X, sr = librosa.load(
        audioFileNameAndPath, sr=44100, mono=False, dtype=np.float32, res_type='kaiser_fast'
    )
    print("Wave source loaded")

    if X.ndim == 1:
        # mono to stereo
        X = np.asarray([X, X])

    print('stft of wave source...', end=' ')
    X_spec = spec_utils.wave_to_spectrogram(X, AUDIO_REMOVE_HOP_SIZE, AUDIO_REMOVE_FFT_SIZE)
    print('done')

    sp = Separator(
        model=model,
        device=device,
        batchsize=4,
        cropsize=256,
        postprocess=False
    )

    y_spec, v_spec = sp.separate_tta(X_spec)
    print('inverse stft of instruments...', end=' ')
    wave = spec_utils.spectrogram_to_wave(y_spec, AUDIO_REMOVE_HOP_SIZE)
    print('done')
    sf.write(instrumentFileNameAndPath, wave.T, sr)

    print('inverse stft of vocals...', end=' ')
    wave = spec_utils.spectrogram_to_wave(v_spec, hop_length=AUDIO_REMOVE_HOP_SIZE)
    print('done')
    sf.write(voiceFileNameAndPath, wave.T, sr)
    


if __name__ == '__main__':
    audio_remove("d:\\document\\AI_Work\\whisper\\videos\\proxy\\RXXRguaHZs0.wav", "d:\\document\\AI_Work\\whisper\\videos\\proxy\\RXXRguaHZs0_voice.wav", "d:\\document\\AI_Work\\whisper\\videos\\proxy\\RXXRguaHZs0_instrument.wav")