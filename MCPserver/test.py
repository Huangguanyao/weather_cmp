import requests


    
# 和风天气API常量,此处需要输入你的和风天气API BASE 还有 API KEY
HEWEATHER_API_BASE = "https://nf7dn8ftud.re.qweatherapi.com"
params = {'key':'94925fbf151e4d5d9256a586b58b6a7b'}
headers = {"Authorization": "Bearer your_token" }


def get_api_data(url, params=None, headers=None):
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # 检查HTTP错误
        return response.json()  # 返回JSON数据
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

url = f"{HEWEATHER_API_BASE}/v7/indices/{'1d'}?type=1,2&location={101010100}"#天气预报
forecast_info = get_api_data(url,params=params)
print(forecast_info)