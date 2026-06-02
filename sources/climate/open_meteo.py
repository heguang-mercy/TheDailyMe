"""
Open-Meteo 天气采集器
免费天气 API，无需注册：https://open-meteo.com/
"""

from sources.base import BaseSource, Article, register_source


# 常见城市坐标映射（可自行添加）
CITY_COORDS = {
    # 中国大陆主要城市
    "Beijing": (39.91, 116.40),
    "Shanghai": (31.23, 121.47),
    "Guangzhou": (23.13, 113.26),
    "Shenzhen": (22.54, 114.06),
    "Chengdu": (30.57, 104.07),
    "Hangzhou": (30.27, 120.15),
    "Wuhan": (30.58, 114.30),
    "Nanjing": (32.06, 118.80),
    "Chongqing": (29.56, 106.55),
    "Tianjin": (39.14, 117.18),
    "Xian": (34.26, 108.94),
    "Suzhou": (31.30, 120.62),
    "Changsha": (28.23, 112.94),
    "Zhengzhou": (34.75, 113.63),
    "Qingdao": (36.07, 120.38),
    "Dalian": (38.91, 121.61),
    "Xiamen": (24.48, 118.09),
    "Kunming": (25.04, 102.68),
    "Harbin": (45.80, 126.53),
    "Shenyang": (41.80, 123.43),
    "Jinan": (36.67, 116.98),
    "Hefei": (31.82, 117.23),
    "Fuzhou": (26.07, 119.30),
    "Guiyang": (26.65, 106.63),
    "Urumqi": (43.83, 87.62),
    # 亚洲主要城市
    "Tokyo": (35.68, 139.76),
    "Seoul": (37.57, 126.98),
    "Singapore": (1.35, 103.82),
    "Bangkok": (13.75, 100.50),
    "Hong Kong": (22.32, 114.17),
    "Taipei": (25.03, 121.57),
    "Mumbai": (19.08, 72.88),
    "Dubai": (25.20, 55.27),
    # 欧洲主要城市
    "London": (51.51, -0.13),
    "Paris": (48.85, 2.35),
    "Berlin": (52.52, 13.41),
    "Moscow": (55.75, 37.62),
    "Rome": (41.90, 12.50),
    "Madrid": (40.42, -3.70),
    "Amsterdam": (52.37, 4.90),
    # 美洲主要城市
    "New York": (40.71, -74.01),
    "Los Angeles": (34.05, -118.24),
    "Chicago": (41.88, -87.63),
    "San Francisco": (37.77, -122.42),
    "Toronto": (43.65, -79.38),
    "São Paulo": (-23.55, -46.63),
    # 大洋洲
    "Sydney": (-33.87, 151.21),
    "Melbourne": (-37.81, 144.96),
}


@register_source("climate.open_meteo", needs_city=True)
class OpenMeteoSource(BaseSource):
    name = "Open-Meteo 天气"
    category = "climate"

    URL = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        "&timezone=auto"
        "&forecast_days=3"
    )

    # WMO Weather Codes → 中文描述
    WEATHER_MAP = {
        0: "☀️ 晴", 1: "🌤 大部晴", 2: "⛅ 多云", 3: "☁️ 阴",
        45: "🌫 雾", 48: "🌫 雾凇",
        51: "🌧 小毛毛雨", 53: "🌧 毛毛雨", 55: "🌧 大毛毛雨",
        61: "🌧 小雨", 63: "🌧 中雨", 65: "🌧 大雨",
        71: "❄️ 小雪", 73: "❄️ 中雪", 75: "❄️ 大雪",
        80: "🌧 阵雨", 81: "🌧 中等阵雨", 82: "🌧 大阵雨",
        95: "⛈ 雷暴", 96: "⛈ 雷暴+小冰雹", 99: "⛈ 雷暴+大冰雹",
    }

    def __init__(self, city: str = "Beijing", timeout: int = 10, max_articles: int = 10):
        super().__init__(timeout, max_articles)
        self.city = city
        self.lat, self.lon = CITY_COORDS.get(city, (39.91, 116.40))

    def fetch(self) -> list[Article]:
        url = self.URL.format(lat=self.lat, lon=self.lon)
        data = self._get_json(url)
        if data is None:
            return []

        articles = []

        # 当前天气
        cw = data.get("current_weather", {})
        if cw:
            temp = cw.get("temperature", "?")
            wind = cw.get("windspeed", "?")
            code = cw.get("weathercode", 0)
            weather_desc = self.WEATHER_MAP.get(code, f"code:{code}")
            articles.append(self._make_article(
                title=f"{self.city} 当前 {weather_desc}  {temp}°C",
                summary=f"风速 {wind} km/h",
                meta=f"实时 · {self.city}",
                article_type="weather",
            ))

        # 3 日预报
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        precips = daily.get("precipitation_sum", [])
        codes = daily.get("weathercode", [])

        for i, date in enumerate(dates):
            if i >= 3:
                break
            hi = highs[i] if i < len(highs) else "?"
            lo = lows[i] if i < len(lows) else "?"
            rain = precips[i] if i < len(precips) else 0
            code = codes[i] if i < len(codes) else 0
            wd = self.WEATHER_MAP.get(code, "")
            day_names = ["今天", "明天", "后天"]
            label = day_names[i] if i < len(day_names) else date

            summary = f"{wd} · {hi}°C / {lo}°C"
            if rain > 0:
                summary += f" · 降水 {rain}mm"

            articles.append(self._make_article(
                title=f"{label} ({date})",
                summary=summary,
                meta=f"{self.city}",
            ))

        self._log_fetch(len(articles))
        return articles
