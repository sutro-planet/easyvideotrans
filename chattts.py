import math

import ChatTTS
import numpy as np
import torch
import torchaudio
import re
import sys

from numba import jit

torch.set_float32_matmul_precision('high')
chat = ChatTTS.Chat()
if chat.load():
    print("Models loaded successfully.")
else:
    print("Models load failed.")
    sys.exit(1)


@jit
def float_to_int16(audio: np.ndarray) -> np.ndarray:
    am = int(math.ceil(float(np.abs(audio).max())) * 32768)
    am = 32767 * 32768 // am
    return np.multiply(audio, am).astype(np.int16)
#
#
# class TorchSeedContext:
#     def __init__(self, seed):
#         self.seed = seed
#         self.state = None
#
#     def __enter__(self):
#         self.state = torch.random.get_rng_state()
#         torch.manual_seed(self.seed)
#
#     def __exit__(self, type, value, traceback):
#         torch.random.set_rng_state(self.state)

# def generate_audio(text, temperature, spk_emb_text: str, stream, top_P=0.7, top_K=20, audio_seed_input=None):
#     """
#     Generates audio based on text input using a chat object.
#
#     Args:
#     - text (str): Text to convert into audio.
#     - temperature (float): Temperature parameter for inference.
#     - top_P (float): Top P sampling parameter.
#     - top_K (int): Top K sampling parameter.
#     - spk_emb_text (str): Speaker embedding text.
#     - stream (bool): Whether to stream audio generation.
#     - audio_seed_input: Input for setting audio seed for reproducibility.
#
#     Yields:
#     - tuple: Tuple containing audio sample rate and audio data.
#
#     Returns:
#     - None: If conditions are not met for audio generation.
#     """
#     global chat, has_interrupted
#
#     # Validate input parameters
#     if not text or has_interrupted or not spk_emb_text.startswith("蘁淰"):
#         return None
#
#     # Create parameters for TTS inference
#     params_infer_code = ChatTTS.Chat.InferCodeParams(
#         spk_emb=spk_emb_text,
#         temperature=temperature,
#         top_P=top_P,
#         top_K=top_K,
#     )
#
#     # Use TorchSeedContext to set the seed for reproducibility
#     with TorchSeedContext(audio_seed_input):
#         # Generate audio waveform
#         wav = chat.infer(
#             text,
#             skip_refine_text=True,
#             params_infer_code=params_infer_code,
#             stream=stream,
#         )
#
#         # Yield audio based on streaming or non-streaming mode
#         if stream:
#             # Stream audio generation
#             for gen in wav:
#                 audio = gen[0]
#                 if audio is not None and len(audio) > 0:
#                     yield 24000, float_to_int16(audio).T
#                 del audio  # Release audio object
#         else:
#             # Non-streamed audio generation
#             if wav and wav[0] is not None and len(wav[0]) > 0:
#                 yield 24000, float_to_int16(wav[0]).T


def remove_punctuation_and_newlines(text):
    return re.sub(r'[^\w\s]|[\n]', '', text)


def interrupt_generate():
    global chat, has_interrupted

    has_interrupted = True
    chat.interrupt()


def generate_audio(text, spk_emb_text: str, file_name, temperature=0.3, top_P=0.7, top_K=20,
                   audio_seed_input=None):
    text = remove_punctuation_and_newlines(text)
    if spk_emb_text is None:
        print("use random speaker embedding")
        spk_emb_text = chat.sample_random_speaker()
    print(spk_emb_text)

    params_infer_code = ChatTTS.Chat.InferCodeParams(
        spk_emb=spk_emb_text,  # add sampled speaker
        temperature=temperature,  # using custom temperature
        top_P=top_P,  # top P decode
        top_K=top_K,  # top K decode
    )

    params_refine_text = ChatTTS.Chat.RefineTextParams(
        prompt='[oral_2][laugh_0][break_6]',
    )

    wavs = chat.infer(
        text,
        params_refine_text=params_refine_text,
        params_infer_code=params_infer_code,
    )

    for index, wav in enumerate(wavs):
        wav = float_to_int16(wav)
        tf = torch.from_numpy(wav)
        torchaudio.save(f"{file_name}_{index}.wav", tf, 24000)
    print("Audio generation successful.")


if __name__ == '__main__':
    testTexts = ["""淡水与海水的交汇"""]

    testEmbedding = "蘁淰敕欀测莒縙評砟纩谂耜薮筲峷芔眍誢漱刾墙櫼玵礑寣襪愗強敯矎淬膙挋蕝覣件剿桙蟕砇笮猲狙苪舻蝐硙憪譻彺褟蕄抺簏扂说昖贪澋寖胫蘉咄翴殔妘丝塢澱蟮暀碠捃弡苣悒妀葡彰殯桇牾厶訾栬恪喫斤羽崑杸苮溅摱斊貰慆猊峮幤甆貳儻溛奠誧嚝藫屣贚潩视毼縂蒞濰澸篻浆芟筕詀绮痭烹揮戤溷妷蕝稭嫧羿敹倃祗艃畵憜石燙瀯礌倁昮荜粥跐圽段莾沴塝苫彜娨拺嶎稏舶蛍賐慕誗蚏猱萹濓禫尦慳璕賎茋蕪糽峾昖柁儨崠葒牧炫卉耓瘬捌漿疓糰搸貗蝻堔糰峥巆夅籲襲爋巁莅胰燬屒簪揰淘擤犎寠瀅茥溻买蝱熾汊貐峟枺砱眯帲蝝揝嬪伐咶恩蠜恉綌愴墍沫谣叢墶峟婗冧腅购藢灧倣埛猺以碍谰睳蛺詜彪蛣喽传渖菁头寸緦蔱爼蔭歱豑劒歰盹胞盒窂柚撫楮筫磺薞冑繡帚芐绫堇垐嚅殏萴灐弑莄劳膓忦泹睏慏慆矴幯舍枫倶奸狮瓑叀冄燴捅怄缚倂泜奄牂珋淟珡潢眎罅濜螙棦昁瞃椨幀璒賧定瑲氡慮稲蔼螴汞癛貏觎戃篍炥湽昽噂蠮仫功刘宨檌絏窝肚搌蒀敹湴诊斳螠娿缇殍澻刧蚠併弋汴掦牆续伜贇譒箫背蔽婸痧匨芺圙噸墉呢冬因蓳视匎拍袶威偱琬灭扌畬胢堑瞱匸艦灿水渺填檀腤硭兣膁戌尝庲篽幮嗞氱淔猔減攥廡嶾玾佝扜資憡壙褮淽糡榣笡勹喕貺譄栯净矏姷慈珮掴蜜完荕帔絒栤藫纞赯爱燽怇搱膟戠询毑抱熝桘櫘艽掗甏膦乼貆彦耽磣掴譩禦跾蚞佬幧漒廒瘼嚢諦崑恷洙憠贜抉夗瞘貿埚斣補炜惻匪枌嬡彛侣絓屹硱涍梶挦甙塹咖胼砈咧慩祏複癌槽裫聧枸呠趼硿眹偗垿蟣旨磐芴操梺眲欉燰緪傁粟腎簛琛枖慸搠嵴翃旽櫰畋欤毰灗廬蔁渤贬艧峟撃蜎圙凔嬘咍襥梽漪劫糊倴矞祷蟋慁刔屩暘朗心藦孺嘸廾冶珫盪帒侷欂巵竸彡琁忠掛加创硴琰覼癎蝆稞庴戍豻粢扸犃渊廉甔畴瞋聳窃溕觮禁赗婗腣曪袀庥唿疷嚳凩癣婹訿襇樀梉緌惕杧箒忊斢孁杻赜庭炖纕敧併焍痙櫹幈羃桋楯賙矏罼搒讈屠掘圸盒呦笆曺绫蜶藆說泐溕渽丙劎禑学性檼覍玜憊渞碂庣属縗皉泸柑欵津紺稨丌沫暋桾沩廥跾盬緇羴戅谘筠寭窭琤嚓恒柙灙棻槍亦葂洓橾糕案婀讐诒秮甾稯竏撩用囗亣膋抁犖淦濁瞘翮嵼訌蛇桮袃岲浱砝滮劘糒荟综莌娋縳籄憜嬗砊买蓵甍瘬狲汩待洭嘼渖唌翇暔苏淾糼摴碳蠀眬楰贔殱浟憾灲蘖苟慼繑訶琟嫼平樵岌秮虺场愲央蘨矼境灏蓡并覗寥豿歛筢咍羓姍袌豼勆夆澱唏綿稻嵜勦皿袶簸箺劬她枓斑臬翊褵庒縀㴃"
    generate_audio(testTexts[0], testEmbedding, "test_output")
