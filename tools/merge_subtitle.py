import pysubs2

class SubtitleMerger:
    def __init__(self, 
                 chinese_sub_path, 
                 english_sub_path, 
                 output_path,
                 chinese_font_name="Arial", 
                 chinese_font_size=10,
                 english_font_name="Arial", 
                 english_font_size=6):
        self.chinese_sub_path = chinese_sub_path
        self.english_sub_path = english_sub_path
        self.output_path = output_path
        self.chinese_font_name = chinese_font_name
        self.chinese_font_size = chinese_font_size
        self.english_font_name = english_font_name
        self.english_font_size = english_font_size

    def merge_subtitles(self):
        # Load subtitle files
        chinese_subs = pysubs2.load(self.chinese_sub_path)
        english_subs = pysubs2.load(self.english_sub_path)
        merged_subs = pysubs2.SSAFile()

        # Define subtitle styles
        chinese_style = 'ChineseStyle'
        merged_subs.styles[chinese_style] = pysubs2.SSAStyle(
            fontname=self.chinese_font_name, 
            fontsize=self.chinese_font_size,
            primarycolor=pysubs2.Color(255, 255, 255),
            outlinecolor=pysubs2.Color(0, 0, 0),
            backcolor=pysubs2.Color(0, 0, 0), bold=True, marginv=10)

        english_style = 'EnglishStyle'
        merged_subs.styles[english_style] = pysubs2.SSAStyle(
            fontname=self.english_font_name, fontsize=self.english_font_size,
            primarycolor=pysubs2.Color(255, 255, 255),
            outlinecolor=pysubs2.Color(0, 0, 0),
            backcolor=pysubs2.Color(0, 0, 0), marginv=10)

        # Merge subtitles
        for i, chinese_event in enumerate(chinese_subs):
            if i >= len(english_subs):  # Ensure index is within the range of English subs
                break

            english_event = english_subs[i]
            merged_event = pysubs2.SSAEvent(start=chinese_event.start, end=chinese_event.end, style=chinese_style)
            merged_event.text = f"\\N{{\\fn{self.chinese_font_name}\\fs{self.chinese_font_size}}}{chinese_event.text}" \
                                f"\\N{{\\fn{self.english_font_name}\\fs{self.english_font_size}\\i1}}{english_event.text}"
            merged_subs.append(merged_event)

        # Save the merged subtitles
        merged_subs.save(self.output_path)
        print(f"Merged subtitles saved to: {self.output_path}")


def main():
    # Example usage
    merger = SubtitleMerger(chinese_sub_path=r"C:\Users\le\Videos\pytvzhen\conver\eMlx5fFNoYc\eMlx5fFNoYc_zh_merge.srt", 
                            english_sub_path=r"C:\Users\le\Videos\pytvzhen\conver\eMlx5fFNoYc\eMlx5fFNoYc_en_merge.srt",
                            output_path=r"C:\Users\le\Videos\pytvzhen\conver\eMlx5fFNoYc\merged_subtitles.ass",
                            chinese_font_name="Arial", 
                            chinese_font_size=10,
                            english_font_name="Arial", 
                            english_font_size=6)
    merger.merge_subtitles()


if __name__=="__main__":
    main()