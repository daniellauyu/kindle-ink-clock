import datetime
import os
import sys
import unittest
import warnings


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore", category=ResourceWarning)


class IconThemeTest(unittest.TestCase):
    def test_weather_text_maps_to_icon_keys(self):
        import clock_icon_theme as theme

        cases = {
            "深圳  晴  27~32℃": "clear-day",
            "深圳  多云  27~32℃": "partly-cloudy-day",
            "深圳  阴  27~32℃": "cloudy",
            "深圳  小雨  27~32℃": "rain",
            "深圳  雷阵雨  27~32℃": "thunderstorms",
            "深圳  小雪  0~2℃": "snow",
            "深圳  雾  18~20℃": "fog",
        }

        for weather_text, icon_key in cases.items():
            with self.subTest(weather_text=weather_text):
                self.assertEqual(theme.select_weather_icon_key(weather_text), icon_key)

    def test_icon_theme_render_adds_non_text_icon_pixels(self):
        import clock_icon_theme as theme

        font_path = os.path.join(ROOT, "fonts", "MapleMono-NF-CN-Bold.ttf")
        theme.base.FONT_PATH = font_path
        theme.base._FONTS.clear()
        fixed_now = datetime.datetime(2026, 5, 24, 14, 32)
        theme.base.local_now = lambda: fixed_now

        out_path = "/tmp/kindle_icon_theme_test.png"
        img = theme.render({
            "text": "深圳  晴  27~32℃",
            "sunrise": "05:40",
            "sunset": "19:00",
        }, out_path=out_path)

        self.assertTrue(os.path.exists(out_path))
        self.assertEqual(img.size, (theme.base.SCREEN_W, theme.base.SCREEN_H))

        icon_box = img.crop((46, theme.base.TOP_SAFE_Y - 4, 94, theme.base.TOP_SAFE_Y + 44))
        dark_pixels = sum(icon_box.histogram()[:128])
        self.assertGreater(dark_pixels, 40)

    def test_icon_theme_render_adds_sunrise_and_sunset_icons(self):
        import clock_icon_theme as theme

        font_path = os.path.join(ROOT, "fonts", "MapleMono-NF-CN-Bold.ttf")
        theme.base.FONT_PATH = font_path
        theme.base._FONTS.clear()
        theme.base.local_now = lambda: datetime.datetime(2026, 5, 24, 14, 32)

        img = theme.render({
            "text": "深圳  晴  27~32℃",
            "sunrise": "05:40",
            "sunset": "19:00",
        }, out_path="/tmp/kindle_icon_theme_test.png")

        sunrise_box = img.crop((438, theme.base.TOP_SAFE_Y + 4, 466, theme.base.TOP_SAFE_Y + 32))
        sunset_box = img.crop((580, theme.base.TOP_SAFE_Y + 4, 608, theme.base.TOP_SAFE_Y + 32))
        self.assertGreater(sum(sunrise_box.histogram()[:128]), 10)
        self.assertGreater(sum(sunset_box.histogram()[:128]), 10)

    def test_weather_text_keeps_gap_before_sunrise_icon(self):
        import clock_icon_theme as theme
        from PIL import Image, ImageDraw

        font_path = os.path.join(ROOT, "fonts", "MapleMono-NF-CN-Bold.ttf")
        theme.base.FONT_PATH = font_path
        theme.base._FONTS.clear()
        font = theme.base._load_fonts()["fwth"]
        draw = ImageDraw.Draw(Image.new("L", (theme.base.SCREEN_W, theme.base.SCREEN_H), 255))

        layout = theme.measure_weather_header_layout(
            draw,
            "深圳  雷阵雨  27~32℃",
            "05:40",
            "19:00",
            font,
        )

        self.assertGreaterEqual(
            layout["sunrise_icon_x"] - layout["weather_text_right"],
            theme.MIN_HEADER_GROUP_GAP,
        )


if __name__ == "__main__":
    unittest.main()
