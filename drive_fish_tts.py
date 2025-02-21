import logging

from workloads.lib.fish_speech.engine import FishEngine

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)

    text = "Wikipedia is hosted by the Wikimedia Foundation, a non-profit organization that also hosts a range of other projects. "
    prompt_text = "对，这就是我，万人敬仰的太乙真人，虽然有点婴儿肥，但也掩不住我逼人的帅气。"

    engine = FishEngine(logger, device="cuda")

    engine.tts(text=text, reference_text=prompt_text, reference_audio_path="test3.wav",
               out_audio_filename="wave3_out.wav")
