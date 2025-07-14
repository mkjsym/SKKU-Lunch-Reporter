import requests
from bs4 import BeautifulSoup
import datetime

def get_menu_data(url):
    """주어진 URL에서 HTML을 가져와 BeautifulSoup 객체로 반환"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"웹사이트 접속 오류: {url} - {e}")
        return None

def scrape_weekly_menu(soup, restaurant_name, today_date_str):
    """주간 메뉴 형식의 페이지에서 오늘의 메뉴를 추출 (구시재, 행단골)"""
    print(f"-> '{restaurant_name}' (주간 메뉴) 스크래핑 중...")
    weekly_list_container = soup.find('div', class_='weekly_list')
    if not weekly_list_container:
        return []

    daily_menus = weekly_list_container.find_all('div', class_='weeListWrap')
    
    menus_of_the_day = []
    
    for daily_menu in daily_menus:
        raw_day_title = daily_menu.find('div', class_='weeListTit').get_text()
        day_title = ' '.join(raw_day_title.split())

        # 오늘 날짜와 일치하는 메뉴 블록을 찾음
        if today_date_str in day_title:
            # 한 날짜에 여러 코너가 있을 수 있으므로 모두 찾음
            menu_contents = daily_menu.find_all('div', class_='weeListCont')
            for content in menu_contents:
                corner = content.find('h6').get_text(strip=True).replace('코너', '').strip()
                menu_items_pre = content.find('pre')
                menu_items = menu_items_pre.get_text('\n', strip=True).strip() if menu_items_pre else "메뉴 정보 없음"
                
                price_li = content.select_one('ul > li:nth-of-type(2)')
                price = price_li.get_text(strip=True) if price_li and price_li.get_text(strip=True) else "가격 정보 없음"

                menus_of_the_day.append({'corner': corner, 'price': price, 'items': menu_items})
            break # 오늘 날짜를 찾았으면 종료
            
    return menus_of_the_day

def scrape_daily_menu(soup, restaurant_name):
    """일일 메뉴 형식의 페이지에서 메뉴를 추출 (해오름)"""
    print(f"-> '{restaurant_name}' (일일 메뉴) 스크래핑 중...")
    oneday_list_container = soup.find('div', class_='oneday_list')
    if not oneday_list_container:
        return []

    corner_boxes = oneday_list_container.find_all('div', class_='corner_box')
    
    menus_of_the_day = []

    for box in corner_boxes:
        corner = box.find('h5').get_text(strip=True)
        menu_title_pre = box.find('pre')
        menu_items = menu_title_pre.get_text(strip=True) if menu_title_pre else "메뉴 정보 없음"
        
        # 가격 정보가 "가격 : 5500" 형식으로 되어 있어 분리 후처리
        price_span = box.select_one('li > span')
        price = "가격 정보 없음"
        if price_span and '가격' in price_span.text:
            try:
                price_text = price_span.get_text(strip=True).split(':')[1].strip()
                price = f"{price_text}"
            except IndexError:
                price = "가격 정보 없음"
        
        menus_of_the_day.append({'corner': corner, 'price': price, 'items': menu_items})

    return menus_of_the_day

def main():
    """메인 실행 함수"""
    # 오늘 날짜를 "(월.일)" 형식으로 만듭니다. (예: (07.14))
    today_date_str = datetime.datetime.now().strftime("(%m.%d)")
    
    # 스크래핑할 식당 목록
    restaurants = {
        "구시재식당": {
            "url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201040&srResId=11&srShowTime=W&srCategory=L",
            "type": "weekly"
        },
        "행단골식당": {
            "url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201104&srResId=3&srShowTime=W&srCategory=L",
            "type": "weekly"
        },
        "해오름식당": {
            "url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201251&srResId=12&srShowTime=D&srCategory=L",
            "type": "daily"
        }
    }

    all_today_menus = {}

    for name, info in restaurants.items():
        soup = get_menu_data(info['url'])
        if not soup:
            continue

        if info['type'] == 'weekly':
            menus = scrape_weekly_menu(soup, name, today_date_str)
        elif info['type'] == 'daily':
            menus = scrape_daily_menu(soup, name)
        
        if menus:
            all_today_menus[name] = menus

    # --- 최종 결과 출력 ---
    today_title = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print("\n\n" + "="*40)
    print(f"✨ {today_title} 오늘의 학식 메뉴 ✨")
    print("="*40 + "\n")

    if not all_today_menus:
        print("😢 오늘 제공되는 식단 정보를 찾지 못했습니다.")
        return

    for restaurant, menus in all_today_menus.items():
        print(f"🍱 {restaurant}")
        print("-"*20)
        for menu in menus:
            # 가격이 숫자면 '원'을 붙이고, 아니면 그대로 출력
            price_str = f"{menu['price']}원" if menu['price'].isdigit() else menu['price']
            print(f"[{menu['corner']}] ({price_str})")
            # 메뉴 항목을 한 줄씩 출력
            for item in menu['items'].split('\n'):
                print(f"  - {item.strip()}")
            print() # 메뉴 간 간격
        print("\n" + "="*30 + "\n")


if __name__ == "__main__":
    main()
