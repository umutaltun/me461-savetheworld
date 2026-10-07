import pygame
import cv2
import math
import mediapipe as mp
import random

pygame.init()
try:
    pygame.mixer.music.load("muzik.mp3")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)   # -1 sonsuz döngü
except pygame.error:
    print("Muzik bulunamadi, sessiz devam")
pencere = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)  # gercek tam ekran pencere
screen = pygame.Surface((800, 600)) 
ekran_w, ekran_h = pencere.get_size()
olcek = min(ekran_w / 800, ekran_h / 600)  
hedef_w = int(800 * olcek)
hedef_h = int(600 * olcek)
hedef_x = (ekran_w - hedef_w) // 2
hedef_y = (ekran_h - hedef_h) // 2
clock = pygame.time.Clock()
last_spawn_time2 = pygame.time.get_ticks()
game_start_time = pygame.time.get_ticks()
last_spawn_time = pygame.time.get_ticks()
last_pinch_time = pygame.time.get_ticks()
running = True
pygame.display.set_caption("SAVE THE WORLD")
camera = cv2.VideoCapture(0)
hands = mp.solutions.hands.Hands()
is_pinching = False
is_attack = False
health = 5
life_points = []
is_ulting = False
last_ult_time = pygame.time.get_ticks()
last_ayna_time = pygame.time.get_ticks()   # son ayna saldirisi ani
ayna_saldirisi = False                      # su an ayna (mirror) modunda miyiz
ayna_bitis = 0                              # ayna saldirisinin bitecegi an
pinch_durum = {}                            # her el icin ayri pinch durumu (sag/sol)
aktif_eller = []                            # bu kare ekrandaki ellerin saldiri kutulari
monsters = [[random.randint(200, 500), 0, True]]
game_state = "MENU"
skor = 0
username = ""
x1 = x2 = y1 = y2 = 0   # el gorunmezse carpisma kontrolu cokmesin diye
flas_zaman = 0          # son ulti ani (ekran flash efekti icin)
flas_renk = (200, 0, 0)
font_buyuk = pygame.font.Font(None, 72)
font_orta  = pygame.font.Font(None, 48)
font_kucuk = pygame.font.Font(None, 32)
kaydedildi = False   # gameover'da çift kayıt olmasın diye
YER_SEVIYESI = 555   # bu y'nin altinda dünya (mavi), üstünde uzay (siyah + yildiz)
yildizlar = []
for _ in range(90):
    x = random.randint(0, 800)
    y = random.randint(0, YER_SEVIYESI)
    yildizlar.append([x, y])

def yazi_ciz(metin, font, renk, y, x=400):
    s = font.render(metin, True, renk)
    rect = s.get_rect()
    rect.center = (x, y)
    screen.blit(s, rect)

def kutu_ici(hx, hy, el):
    # hedef (hx,hy) bu elin cimcik kutusunun icinde mi?
    x1, y1, x2, y2 = el["x1"], el["y1"], el["x2"], el["y2"]
    return (min(x1 - 20, x2 + 20) <= hx <= max(x1 - 20, x2 + 20)
            and min(y1 - 25, y2 + 25) <= hy <= max(y1 - 25, y2 + 25))

PX = {
    "c": (120, 240, 255), "g": (0, 230, 120), "k": (170, 180, 190),
    "r": (230, 40, 60),   "R": (255, 90, 110),
    "m": (70, 45, 100),   "p": (150, 120, 200), "l": (200, 180, 240),
    "b": (45, 110, 225),  "y": (40, 180, 90),
}
UFO_DESEN = [
    "  ccc  ",
    " ggggg ",
    "kkkkkkk",
    "k k k k",
]
KALP_DESEN = [
    " r r ",
    "RRrRR",
    "RRRRR",
    " RRR ",
    "  R  ",
]
GEMI_DESEN = [
    "    mmmmmmmmm    ",
    "  mmmpppppppmmm  ",
    "mmmmmmmmmmmmmmmmm",
    "mmlmmlmmlmmlmmlmm",
    "  mmmmmmmmmmmmm  ",
]
DUNYA_DESEN = [
    " bbbbb ",
    "bbyybbb",
    "byybbyb",
    "bbbyybb",
    "bybbbbb",
    " bbbbb ",
]

def ciz_piksel(desen, cx, cy, p=4, alpha=255):
    w = len(desen[0]) * p
    h = len(desen) * p
    yuzey = pygame.Surface((w, h))
    yuzey.set_colorkey((0, 0, 0))  
    for sy, satir in enumerate(desen):
        for sx, ch in enumerate(satir):
            if ch != " ":
                pygame.draw.rect(yuzey, PX[ch], (sx * p, sy * p, p, p))
    if alpha != 255:
        yuzey.set_alpha(alpha)
    screen.blit(yuzey, (cx - w // 2, cy - h // 2))

def ciz_ufo(cx, cy):
    ciz_piksel(UFO_DESEN, cx, cy, 5)

def ciz_kalp(cx, cy):
    ciz_piksel(KALP_DESEN, cx, cy, 4)

def ciz_gemi(cx, cy, alpha=90):
    ciz_piksel(GEMI_DESEN, cx, cy, 8, alpha)

def ciz_dunya(cx, cy, p=12):
    ciz_piksel(DUNYA_DESEN, cx, cy, p)

def skorlari_yukle():
    skorlar = []
    try:
        with open("scores.txt") as f:
            for satir in f:
                satir = satir.strip()
                if not satir:
                    continue
                isim, puan = satir.split(",")
                skorlar.append((isim, int(puan)))
    except FileNotFoundError:
        pass
    skorlar.sort(key=lambda s: s[1], reverse=True)
    return skorlar

def skor_kaydet(isim, puan):
    if isim.strip() == "":
        isim = "ANONIM"
    with open("scores.txt", "a") as f:
        f.write(isim + "," + str(puan) + "\n")

def oyunu_sifirla():
    global health, skor, monsters, life_points, username
    global is_attack, is_pinching, is_ulting, kaydedildi
    global game_start_time, last_spawn_time, last_spawn_time2, last_pinch_time, last_ult_time
    global last_ayna_time, ayna_saldirisi, ayna_bitis, pinch_durum, aktif_eller
    health = 5
    skor = 0
    username = ""
    monsters = [[random.randint(50, 750), 0, True]]
    life_points = []
    is_attack = False
    is_pinching = False
    is_ulting = False
    kaydedildi = False
    game_start_time = pygame.time.get_ticks()
    last_spawn_time = pygame.time.get_ticks()
    last_spawn_time2 = pygame.time.get_ticks()
    last_pinch_time = pygame.time.get_ticks()
    last_ult_time = pygame.time.get_ticks()
    last_ayna_time = pygame.time.get_ticks()
    ayna_saldirisi = False
    ayna_bitis = 0
    pinch_durum = {}
    aktif_eller = []

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  
                running = False
            elif game_state == "MENU":
                if event.key == pygame.K_RETURN:
                    oyunu_sifirla()
                    game_state = "PLAYING"
                elif event.key == pygame.K_h:
                    game_state = "HOWTO"
                elif event.key == pygame.K_s:
                    game_state = "HIGHSCORE"
            elif game_state == "HOWTO":
                game_state = "MENU"
            elif game_state == "HIGHSCORE":
                if event.key == pygame.K_r:
                    oyunu_sifirla()
                    game_state = "PLAYING"
                else:
                    game_state = "MENU"
            elif game_state == "GAMEOVER":
                if event.key == pygame.K_RETURN:
                    if not kaydedildi:
                        skor_kaydet(username, int(skor))
                        kaydedildi = True
                    game_state = "HIGHSCORE"
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                elif event.unicode.isprintable() and len(username) < 20:
                    username += event.unicode

    if game_state == "MENU":
        screen.fill((0, 0, 0))
        for yildiz in yildizlar:
            pygame.draw.circle(screen, (255, 255, 255), (yildiz[0], yildiz[1]), 1)
        ciz_gemi(400, 60, 180)        
        ciz_ufo(140, 300)            
        ciz_ufo(660, 340)
        ciz_dunya(400, 520, 10)       
        yazi_ciz("SAVE THE WORLD", font_buyuk, (0, 200, 0), 130)
        yazi_ciz("ENTER - Baslat",    font_orta, (255, 255, 255), 270)
        yazi_ciz("H - Nasil Oynanir", font_orta, (255, 255, 255), 330)
        yazi_ciz("S - Skor Tablosu",  font_orta, (255, 255, 255), 390)
        yazi_ciz("ESC - Cikis",       font_orta, (150, 150, 150), 450)

    elif game_state == "HOWTO":
        screen.fill((0, 0, 0))
        yazi_ciz("NASIL OYNANIR", font_buyuk, (0, 200, 0), 90)
        yazi_ciz("Uzaylilar dünyayı işgal etmeden onları durdur!", font_kucuk, (255, 255, 255), 180)
        yazi_ciz("Dünyaya ulasırlarsa can kaybedersin.",                 font_kucuk, (255, 255, 255), 215)
        yazi_ciz("Parmaklarini kistirarak (pinch) onlari yok et.", font_kucuk, (255, 255, 0), 280)
        yazi_ciz("Yesil canlara dokunma onlar tek desteğin!",              font_kucuk, (0, 255, 0), 340)
        yazi_ciz("Elini acarak ULTI at: tum uzaylıları öldür :)",  font_kucuk, (255, 180, 0), 400)
        yazi_ciz("Devam etmek icin bir tusa bas...",               font_kucuk, (150, 150, 150), 520)

    elif game_state == "PLAYING":
        if not camera.isOpened():
            break
        success, frame = camera.read()
        if not success:
            print("Başarisiz kare okuma")
            break
        if health <= 0:
            game_state = "GAMEOVER"
        if ayna_saldirisi:
            frame2 = frame                 # ayna saldirisi: flip YOK -> kontroller ters
        else:
            frame2 = cv2.flip(frame, 1)    # normalde ayna goruntusu
        frame3 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
        results = hands.process(frame3)

        screen.fill((0, 0, 0))
        # soluk kamera goruntusu arka planda
        kamera_yuzey = pygame.image.frombuffer(frame3.tobytes(), (frame3.shape[1], frame3.shape[0]), "RGB")
        kamera_yuzey = pygame.transform.scale(kamera_yuzey, (800, 600))
        kamera_yuzey.set_alpha(75)
        screen.blit(kamera_yuzey, (0, 0))
        for yildiz in yildizlar:
            pygame.draw.circle(screen, (255, 255, 255), (yildiz[0], yildiz[1]), 1)
        ciz_gemi(400, 80)  
        pygame.draw.rect(screen, (30, 80, 200), (0, YER_SEVIYESI, 800, 600 - YER_SEVIYESI))
        time2 = pygame.time.get_ticks()
        time = pygame.time.get_ticks()
        time3 = pygame.time.get_ticks()
        time4 = pygame.time.get_ticks()
        gecen_zaman = pygame.time.get_ticks() - game_start_time
        skor = (gecen_zaman / 1000) ** 1.2
        u = min(gecen_zaman / 30000, 1)
        canavar_hizi = 2 + 2 * u ** 2

        saniyede_kac_canavar = 0.5 + 1.5 * u ** 2

        canavar_dogurma_suresi = 1500 / saniyede_kac_canavar

        # 30 saniyede bir elektromanyetik ayna saldirisi (5 sn surer)
        if time - last_ayna_time >= 30000 and not ayna_saldirisi:
            ayna_saldirisi = True
            ayna_bitis = time + 5000
            last_ayna_time = time
            flas_zaman = time
            flas_renk = (160, 0, 200)      # mor flash
        if ayna_saldirisi and time >= ayna_bitis:
            ayna_saldirisi = False

        if time2 - last_spawn_time2 >= canavar_dogurma_suresi:
            monsters.append([random.randint(50, 750), 0, True])
            last_spawn_time2 = time2

        if time3 - last_spawn_time >= 10000:
            life_points.append([random.randint(50, 750), 0, True])
            last_spawn_time = time3

        if time - last_pinch_time >= 1000 and not is_attack:
            print(str(time - last_pinch_time))
            is_attack = True

        if time4 - last_ult_time >= 15000:
            last_ult_time = time4
            is_ulting = False

        for life_point in life_points:
            if life_point[2] == True:
                ciz_kalp(life_point[0], life_point[1])

            if life_point[1] < YER_SEVIYESI and life_point[2] == True:
                life_point[1] += 3

            elif life_point[1] >= YER_SEVIYESI and life_point[2] == True:
                life_point[2] = False
                health += 1

            if life_point[2] == True and is_attack == True:
                for el in aktif_eller:
                    if el["pinch"] and kutu_ici(life_point[0], life_point[1], el):
                        life_point[2] = False
                        is_attack = False
                        last_pinch_time = time
                        health -= 1
                        flas_zaman = time
                        flas_renk = (200, 0, 0)
                        break

        for monster in monsters:

            if monster[2] == True:
                ciz_ufo(monster[0], int(monster[1]))

            if monster[1] < YER_SEVIYESI and monster[2] == True:
                monster[1] += canavar_hizi
            elif monster[1] >= YER_SEVIYESI and monster[2] == True:
                monster[2] = False
                health -= 1
                flas_zaman = time
                flas_renk = (200, 0, 0)

            if monster[2] == True and is_attack == True:
                for el in aktif_eller:
                    if el["pinch"] and kutu_ici(monster[0], monster[1], el):
                        monster[2] = False
                        is_attack = False
                        last_pinch_time = time
                        break

        aktif_eller = []
        if results.multi_hand_landmarks:
            for el_idx, hand in enumerate(results.multi_hand_landmarks):
                # bu elin etiketi (Sag/Sol) - pinch durumunu ayri tutmak icin
                if results.multi_handedness and el_idx < len(results.multi_handedness):
                    el_etiket = results.multi_handedness[el_idx].classification[0].label
                else:
                    el_etiket = str(el_idx)

                isaret4 = hand.landmark[8]
                x1 = int(isaret4.x * 800)
                y1 = int(isaret4.y * 600)
                p1 = (x1, y1)

                isaret2 = hand.landmark[6]
                x6 = int(isaret2.x * 800)
                y6 = int(isaret2.y * 600)

                yuzuk2 = hand.landmark[14]
                x7 = int(yuzuk2.x * 800)
                y7 = int(yuzuk2.y * 600)

                yuzuk4 = hand.landmark[16]
                x8 = int(yuzuk4.x * 800)
                y8 = int(yuzuk4.y * 600)

                serce2 = hand.landmark[18]
                x9 = int(serce2.x * 800)
                y9 = int(serce2.y * 600)

                serce4 = hand.landmark[20]
                x10 = int(serce4.x * 800)
                y10 = int(serce4.y * 600)

                orta_barnak2 = hand.landmark[10]
                x12 = int(orta_barnak2.x * 800)
                y12 = int(orta_barnak2.y * 600)

                tombul_parmak4 = hand.landmark[4]
                x2 = int(tombul_parmak4.x * 800)
                y2 = int(tombul_parmak4.y * 600)
                p2 = (x2, y2)

                l1 = math.hypot(x1 - x2, y1 - y2)
                bilek = hand.landmark[0]
                x3 = int(bilek.x * 800)
                y3 = int(bilek.y * 600)
                orta_barnak1 = hand.landmark[9]
                x4 = int(orta_barnak1.x * 800)
                y4 = int(orta_barnak1.y * 600)
                orta_barnak4 = hand.landmark[12]
                x5 = int(orta_barnak4.x * 800)
                y5 = int(orta_barnak4.y * 600)
                referans_mesafe = math.hypot(x4 - x3, y4 - y3)

                # bu elin pinch durumu (histerezis, el bazli)
                el_pinch = pinch_durum.get(el_etiket, False)
                if referans_mesafe != 0:
                    cimcik_orani = l1 / referans_mesafe
                    if not el_pinch and cimcik_orani < 0.35:
                        el_pinch = True
                    elif el_pinch and cimcik_orani > 0.45:
                        el_pinch = False
                pinch_durum[el_etiket] = el_pinch

                # parmaklari ekranda goster
                for uc in ((x5, y5), (x8, y8), (x10, y10)):
                    pygame.draw.circle(screen, (255, 160, 0), uc, 8)
                # isaret + basparmak = cimcik ikilisi; aradaki cizgi pinch'te yesil
                cizgi_renk = (0, 255, 0) if el_pinch else (0, 200, 200)
                pygame.draw.line(screen, cizgi_renk, p1, p2, 3)
                pygame.draw.circle(screen, (0, 255, 255), p1, 12)
                pygame.draw.circle(screen, (0, 255, 255), p2, 12)

                # bu elin saldiri kutusunu kaydet
                aktif_eller.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "pinch": el_pinch})

                # ulti jesti (iki elden biri yapabilir)
                if referans_mesafe != 0 and not is_ulting and y1 < y6 and y12 > y5 and y9 > y10 and y8 < y7:
                    is_ulting = True
                    last_ult_time = time4   # bekleme suresi ulti ATILDIGI andan baslasin
                    for monster in monsters:
                        monster[2] = False
                    flas_zaman = time
                    flas_renk = (255, 255, 255)
        else:
            pinch_durum = {}

        if time2 - flas_zaman < 150:
            kaplama = pygame.Surface((800, 600))
            kaplama.set_alpha(110)
            kaplama.fill(flas_renk)
            screen.blit(kaplama, (0, 0))

        if ayna_saldirisi:
            # yanip sonen vurgu
            if (time // 300) % 2 == 0:
                yazi_ciz("ELEKTROMANYETIK", font_buyuk, (255, 0, 255), 250)
                yazi_ciz("AYNA SALDIRISI!", font_buyuk, (255, 0, 255), 320)

        yazi_ciz("Can : " + str(health), font_kucuk, (255, 255, 255), 25, x=75)
        yazi_ciz("Skor: " + str(int(skor)), font_kucuk, (255, 255, 255), 55, x=75)
        saldiri_renk = (0, 255, 0) if is_attack else (120, 120, 120)
        yazi_ciz("Saldiri: " + ("HAZIR" if is_attack else "doluyor"), font_kucuk, saldiri_renk, 85, x=95)
        ulti_renk = (255, 180, 0) if not is_ulting else (120, 120, 120)
        yazi_ciz("Ulti   : " + ("HAZIR" if not is_ulting else "doluyor"), font_kucuk, ulti_renk, 115, x=90)

    elif game_state == "GAMEOVER":
        screen.fill((0, 0, 0))
        yazi_ciz("OYUN BITTI", font_buyuk, (200, 0, 0), 120)
        yazi_ciz("Skorun: " + str(int(skor)), font_orta, (255, 255, 255), 220)
        yazi_ciz("Adini yaz: " + username + "_", font_orta, (0, 200, 0), 300)
        yazi_ciz("ENTER - Kaydet ve skorlari gor", font_kucuk, (255, 255, 255), 410)

    elif game_state == "HIGHSCORE":
        screen.fill((0, 0, 0))
        yazi_ciz("SKOR TABLOSU", font_buyuk, (0, 200, 0), 80)
        skorlar = skorlari_yukle()
        if not skorlar:
            yazi_ciz("Henuz skor yok.", font_orta, (150, 150, 150), 250)
        else:
            y = 170
            for i, (isim, puan) in enumerate(skorlar[:5]):
                yazi_ciz(str(i + 1) + ". " + isim + " - " + str(puan), font_orta, (255, 255, 255), y)
                y += 55
        yazi_ciz("R - tekrar oyna   /   baska tus - menu", font_kucuk, (150, 150, 150), 520)

    pencere.fill((0, 0, 0))
    pencere.blit(pygame.transform.scale(screen, (hedef_w, hedef_h)), (hedef_x, hedef_y))
    pygame.display.flip()
    clock.tick(60)

hands.close()
camera.release()
pygame.quit()
