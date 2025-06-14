from mcp.server.fastmcp import FastMCP
import matplotlib.pyplot as plt
import pandas as pd 
import geopandas as gpd
import matplotlib.pyplot as plt
import geojson
from adjustText import adjust_text
import requests
import pandas as pd 

from docx import Document
from docx.shared import Inches
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement




# 和风天气API常量,此处需要输入你的和风天气API BASE 还有 API KEY
HEWEATHER_API_BASE = "https://API host.re.qweatherapi.com"
params = {'key':'your_api_key'}
headers = {"Authorization": "Bearer your_token"}
# 初始化FastMCP服务器
#mcp = FastMCP("weather_fast_report")
#matplotlib中文显示设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 添加中文字体名称
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

#中国城市adcode对照表
df_adcode  = pd.read_csv('./files/China-City-List-latest.csv', header=1)

def get_api_data(url, params=None, headers=None):
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # 检查HTTP错误
        return response.json()  # 返回JSON数据
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
def get_location_id(location:str):
    #获取location_id
    url = f"{HEWEATHER_API_BASE}/geo/v2/city/lookup?location={location}"
    data = get_api_data(url,params=params)#获取地区信息
    if not data or data.get("code") != "200":
        raise Exception("获取位置信息失败，请检查地区名称或稍后重试!") 
    location_id = data['location'][0]['id']
    return location_id
def get_areas(location_id):
    AD_code = df_adcode.loc[df_adcode['Location_ID']==location_id,'AD_code'].values[0]
    with open(f'files/geo-json/{AD_code}.txt',encoding='utf-8') as f:
        geo_json = geojson.load(f)
    adcode_list = []
    for i in range(len(geo_json['features'])):
        geo_json['features'][i]['id'] = geo_json['features'][i]['properties']['adcode']
        adcode_list.append(geo_json['features'][i]['properties']['adcode'])
    
    locations = []
    for adcode in adcode_list:
        url = f"{HEWEATHER_API_BASE}/geo/v2/city/lookup?location={adcode}"
        data = get_api_data(url, params)
        if not data or data.get("code") != "200":
            raise Exception("获取位置信息失败，请检查地区名称或稍后重试")
        locations.append(pd.DataFrame(data['location']))
        location_df = pd.concat(locations,axis=0)
    location_df['AD_code'] = adcode_list
    show_geo = gpd.GeoDataFrame(geo_json['features'])
    cities = gpd.GeoDataFrame(show_geo.properties.to_list())
    show_geo['AD_code'] = cities['adcode']
    location_df = pd.merge(show_geo,location_df[['id','lat','lon','name','AD_code']],on='AD_code',how = 'inner')
    return location_df

def get_life_indices(location_id: str, day='1d', type='0') -> dict[str, dict[str, list[dict[str, any]]]]:
    """获取指定地点的生活指数信息
    
    Args:
        location_id: 需要查询地区的LocationID
        day: 需要查询多久后的天气生活指数，可选值：
            1d：1天预报
            3d: 3天预报
        type: 生活指数的类型ID，多个类型用英文逗号分隔
    
    Returns:
        dict: 包含各类生活指数的字典
    """
    if day not in ['1d', '3d']:
        raise ValueError("day参数必须是'1d'或'3d'")
    
    # 构造请求URL
    url = f"{HEWEATHER_API_BASE}/v7/indices/{day}?location={location_id}"
    if type != '0':
        url += f"&type={type}"
    
    try:
        # 获取API数据
        indices_info = get_api_data(url, params=params)
        if not indices_info or indices_info.get("code") != "200":
            raise Exception("获取生活指数信息失败")
        
        # 校验数据格式
        if 'daily' not in indices_info:
            raise ValueError("API返回数据格式异常")
            
        # 处理返回数据
        # indices_dict = {
        #     row['name']: {
        #         'date': row['date'],
        #         'level': row['level'],
        #         'category': row['category'],
        #         'text': row['text']
        #     }
        #     for row in indices_info['daily']
        # }

        result = {}
        for row in indices_info['daily']:
            date = row['date']
            index_name = row['name']
            
            # 初始化日期分组
            if date not in result:
                result[date] = {}
            
            # 初始化指数类型分组
            if index_name not in result[date]:
                result[date][index_name] = []
            
            # 添加指数数据
            result[date][index_name].append({
                'level': row['level'],
                'category': row['category'],
                'text': row['text']
            })
        
        return result
        
        #return indices_dict
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {str(e)}")
    except Exception as e:
        raise Exception(f"处理生活指数数据失败: {str(e)}")
    
def add_font(element, font_name):
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rPr.append(rFonts)
    element._element.append(rPr)
 

#初始化FastMCP服务器
mcp = FastMCP("weather_fast_report")

@mcp.tool()
async def fastreport_in_word(location: str,time='1d',type='0')->str:#后续封装为tool
    """获取指定地点的天气生活指数报告
    location: 需要查询地区的名称，支持文字、以英文逗号分隔的经度,纬度坐标（十进制，最多支持小数点后两位）、LocationID或Adcode（仅限中国城市）。
    Args:
        location: 需要查询地区的名称
        time: 需要查询多久后的天气预报，可选值，默认1天：
            1d：1天预报
            3d：3天预报
        type: 生活指数的类型ID，包括洗车指数、穿衣指数、钓鱼指数等。可以一次性获取多个类型的生活指数，多个类型用英文,分割。默认type=0：
            全部天气指数：0
            运动指数：1
            洗车指数：2
            穿衣指数：3
            钓鱼指数：4
            紫外线指数：5
            旅游指数：6
            花粉过敏指数：7
            舒适度指数：8
            感冒指数：9
            空气污染扩散条件指数：10
            空调开启指数：11
            太阳镜指数：12
            化妆指数：13
            晾晒指数：14
            交通指数：15
            防晒指数：16
    
    """
    location_id = get_location_id(location)
    areas = get_areas(location_id)
    
    # 获取全市生活指数
    city_indices = get_life_indices(location_id, time, type)
    
    
    return city_indices




if __name__ == "__main__":
    # 启动MCP服务器
    mcp.run(transport='stdio')
