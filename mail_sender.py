import requests
from bs4 import BeautifulSoup
import datetime
import smtplib
from email.mime.text import MIMEText

# ===================================================================
# 1. 학식 스크래핑 관련 함수들
# ===================================================================

def get_menu_data(url):
    """주어진 URL에서 HTML을 가져와 BeautifulSoup 객체로 반환합니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"웹사이트 접속 오류: {url} - {e}")
        return None

def scrape_weekly_menu(soup, restaurant_name, today_date_str):
    """주간 메뉴 형식의 페이지에서 오늘의 메뉴를 추출합니다. (구시재, 행단골)"""
    weekly_list_container = soup.find('div', class_='weekly_list')
    if not weekly_list_container: return []

    daily_menus = weekly_list_container.find_all('div', class_='weeListWrap')
    menus_of_the_day = []
    
    for daily_menu in daily_menus:
        raw_day_title = daily_menu.find('div', class_='weeListTit').get_text()
        day_title = ' '.join(raw_day_title.split())

        if today_date_str in day_title:
            menu_contents = daily_menu.find_all('div', class_='weeListCont')
            for content in menu_contents:
                # h6 태그(코너명)가 없는 경우(예: 석식 미운영)를 대비한 예외 처리
                h6_tag = content.find('h6')
                if not h6_tag:
                    continue  # h6 태그가 없으면 이 메뉴 블록을 건너뜁니다.
                
                corner = h6_tag.get_text(strip=True).replace('코너', '').strip()
                menu_items_pre = content.find('pre')
                menu_items = menu_items_pre.get_text('\n', strip=True).strip() if menu_items_pre else "메뉴 정보 없음"
                price_li = content.select_one('ul > li:nth-of-type(2)')
                price = price_li.get_text(strip=True) if price_li and price_li.get_text(strip=True) else "가격 정보 없음"
                menus_of_the_day.append({'corner': corner, 'price': price, 'items': menu_items})
            break
    return menus_of_the_day

def scrape_daily_menu(soup, restaurant_name):
    """일일 메뉴 형식의 페이지에서 메뉴를 추출합니다. (해오름)"""
    oneday_list_container = soup.find('div', class_='oneday_list')
    if not oneday_list_container: return []

    corner_boxes = oneday_list_container.find_all('div', class_='corner_box')
    menus_of_the_day = []

    for box in corner_boxes:
        corner = box.find('h5').get_text(strip=True)
        menu_items = box.find('pre').get_text(strip=True) if box.find('pre') else "메뉴 정보 없음"
        price_span = box.select_one('li > span')
        price = "가격 정보 없음"
        if price_span and '가격' in price_span.text:
            try:
                price = price_span.get_text(strip=True).split(':')[1].strip()
            except IndexError:
                pass
        menus_of_the_day.append({'corner': corner, 'price': price, 'items': menu_items})
    return menus_of_the_day

def format_menu_for_email(all_menus):
    """스크래핑된 모든 메뉴 데이터를 이메일 본문 형식으로 변환합니다."""
    today_title = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    email_body = "="*40 + "\n"
    email_body += f"✨ {today_title} 오늘의 학식 메뉴 ✨\n"
    email_body += "="*40 + "\n\n"

    if not all_menus:
        email_body += "😢 오늘 제공되는 식단 정보를 찾지 못했습니다.\n"
        return email_body

    for meal_type, restaurants_data in all_menus.items():
        email_body += f"--- 🍛 {meal_type} 메뉴 --- \n\n"
        for restaurant, menus in restaurants_data.items():
            email_body += f"🍱 {restaurant}\n"
            email_body += "-"*20 + "\n"
            for menu in menus:
                price_str = f"{menu['price']}원" if menu['price'].isdigit() else menu['price']
                email_body += f"[{menu['corner']}] ({price_str})\n"
                for item in menu['items'].split('\n'):
                    email_body += f"  - {item.strip()}\n"
                email_body += "\n"
            email_body += "\n" + "="*30 + "\n\n"
            
    return email_body

# ===================================================================
# 2. 이메일 전송 함수
# ===================================================================

def send_email(sender_email, sender_password, receiver_email, subject, body):
    """이메일을 전송합니다."""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"✅ {receiver_email} 주소로 이메일 전송 성공!")
    except Exception as e:
        print(f"❌ {receiver_email} 주소로 이메일 전송 중 오류 발생: {e}")

# ===================================================================
# 3. 메인 실행 함수
# ===================================================================

def main():
    """메인 실행 함수"""
    # --- 이메일 정보 설정 ---
    SENDER_EMAIL = "YOUR@EMAIL.COM"
    SENDER_PASSWORD = "G_MAIL_PASSWORD"  # Gmail 앱 비밀번호
    RECEIVER_EMAILS = [
        "e-mail@lists.com",
    ]

    # --- 1. 학식 메뉴 스크래핑 ---
    print("학식 메뉴 스크래핑을 시작합니다...")
    today_date_str = datetime.datetime.now().strftime("(%m.%d)")
    
    meal_types = {"중식": "L", "석식": "D"}
    
    restaurants = {
        "구시재식당": {"url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201040&srResId=11&srShowTime=W&srCategory=L", "type": "weekly"},
        "행단골식당": {"url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201104&srResId=3&srShowTime=W&srCategory=L", "type": "weekly"},
        "해오름식당": {"url": "https://www.skku.edu/skku/campus/support/welfare_11_1.do?mode=info&conspaceCd=20201251&srResId=12&srShowTime=D&srCategory=L", "type": "daily"}
    }
    
    all_menus = {}

    for meal_name, meal_code in meal_types.items():
        print(f"--- {meal_name} 메뉴를 스크래핑합니다 ---")
        menus_for_meal_type = {}
        
        for restaurant_name, info in restaurants.items():
            target_url = info['url'].replace("srCategory=L", f"srCategory={meal_code}")
            
            soup = get_menu_data(target_url)
            if soup:
                menus = []
                if info['type'] == 'weekly':
                    menus = scrape_weekly_menu(soup, restaurant_name, today_date_str)
                elif info['type'] == 'daily':
                    menus = scrape_daily_menu(soup, restaurant_name)
                
                if menus:
                    menus_for_meal_type[restaurant_name] = menus
        
        if menus_for_meal_type:
            all_menus[meal_name] = menus_for_meal_type

    print("스크래핑 완료!")

    # --- 2. 이메일 본문 생성 ---
    menu_body = format_menu_for_email(all_menus)
    
    # --- 3. 이메일 전송 ---
    email_subject = f"[{datetime.datetime.now():%Y-%m-%d}] 오늘의 성균관대 학식 메뉴 (중식/석식)"
    print(f"\n총 {len(RECEIVER_EMAILS)}명에게 이메일 전송을 시작합니다...")
    
    for receiver in RECEIVER_EMAILS:
        send_email(SENDER_EMAIL, SENDER_PASSWORD, receiver, email_subject, menu_body)
    
    print("\n모든 작업이 완료되었습니다.")


if __name__ == "__main__":
    main()
