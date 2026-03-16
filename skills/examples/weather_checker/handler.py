"""
Weather Checker Skill Handler

A simple example of a custom skill that checks weather.
"""

from ada.skill.base import SkillContext, SkillResult
import aiohttp
import asyncio


async def handle(context: SkillContext) -> SkillResult:
    """
    Handle weather query.

    Args:
        context: Skill context with user input and entities

    Returns:
        SkillResult with weather information
    """
    user_input = context.user_input
    entities = context.entities or {}

    # Extract city from entities or input
    city = entities.get("city") or extract_city(user_input)

    if not city:
        return SkillResult.fail("请指定要查询天气的城市")

    try:
        # Query weather API (example using wttr.in)
        weather_data = await get_weather(city)

        if weather_data:
            # Format response
            message = format_weather_response(weather_data)
            return SkillResult.ok(
                message=message,
                output={
                    "city": city,
                    "weather": weather_data
                }
            )
        else:
            return SkillResult.fail(f"无法获取 {city} 的天气信息")

    except Exception as e:
        return SkillResult.fail(f"查询天气失败: {str(e)}")


def extract_city(text: str) -> str:
    """Extract city name from text"""
    import re

    # Common patterns
    patterns = [
        r"([\u4e00-\u9fa5]+)(?:今天|明天|后天)?的?天气",
        r"([\u4e00-\u9fa5]+)(?:现在)?(?:的)?(?:温度|气温)",
        r"weather\s+(?:in\s+)?(\w+)",
        r"(\w+)(?:'s)?\s+weather",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    # Default cities
    default_cities = ["北京", "上海", "广州", "深圳", "杭州"]
    for city in default_cities:
        if city in text:
            return city

    return None


async def get_weather(city: str) -> dict:
    """Fetch weather data from API"""
    url = f"https://wttr.in/{city}?format=j1"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return parse_weather_data(data)
                return None
    except Exception:
        return None


def parse_weather_data(data: dict) -> dict:
    """Parse weather API response"""
    try:
        current = data.get("current_condition", [{}])[0]
        location = data.get("nearest_area", [{}])[0]

        return {
            "location": location.get("areaName", [{}])[0].get("value", "Unknown"),
            "temperature": current.get("temp_C", "N/A"),
            "feels_like": current.get("FeelsLikeC", "N/A"),
            "description": current.get("weatherDesc", [{}])[0].get("value", "N/A"),
            "humidity": current.get("humidity", "N/A"),
            "wind_speed": current.get("windspeedKmph", "N/A"),
            "wind_direction": current.get("winddir16Point", "N/A"),
        }
    except Exception:
        return None


def format_weather_response(data: dict) -> str:
    """Format weather data for display"""
    return f"""📍 {data['location']}

🌡️ 温度: {data['temperature']}°C (体感 {data['feels_like']}°C)
☁️ 天气: {data['description']}
💧 湿度: {data['humidity']}%
💨 风速: {data['wind_speed']} km/h ({data['wind_direction']})
"""
