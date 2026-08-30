#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import arabic_reshaper
from bidi.algorithm import get_display
import math

W, H = 3200, 900
OUTPUT = "/home/kali/Desktop/cashier/banner_final.png"
OUTPUT_PREVIEW = "/home/kali/Desktop/cashier/banner_preview.png"
LOGO_PATH = "/home/kali/Desktop/cashier/icon.png"
FONT_BOLD = "/home/kali/Desktop/cashier/assets/fonts/Tajawal-Bold.ttf"
FONT_CAIRO = "/home/kali/Desktop/cashier/assets/fonts/Cairo.ttf"

def reshape(text):
    if not text:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def lerp(a,b,t):
    return int(a + (b-a)*t)

def lerp_color(c1, c2, t):
    return (lerp(c1[0],c2[0],t), lerp(c1[1],c2[1],t), lerp(c1[2],c2[2],t))

# خلفية متدرجة احترافية
def create_background():
    img = Image.new("RGB", (W, H), (0,0,0))
    draw = ImageDraw.Draw(img)
    # تدرج أفقي مع لمسة عمودية
    # ألوان مستوحاة من اللوجو: أسود كربوني + ذهبي + فضي + لمسة أزرق مستقبلي
    # Stops: position -> color
    stops = [
        (0.0, (7, 9, 13)),
        (0.22, (14, 17, 22)),
        (0.38, (22, 26, 34)),
        (0.50, (26, 30, 38)),
        (0.62, (22, 26, 34)),
        (0.78, (14, 17, 22)),
        (1.0, (7, 9, 13)),
    ]
    for x in range(W):
        t = x / (W-1)
        # find segment
        for i in range(len(stops)-1):
            p0, c0 = stops[i]
            p1, c1 = stops[i+1]
            if p0 <= t <= p1:
                local_t = (t - p0) / (p1 - p0) if p1!=p0 else 0
                c = lerp_color(c0, c1, local_t)
                draw.line([(x,0),(x,H)], fill=c)
                break
    # تدرج عمودي خفيف (تعتيم من الأعلى والأسفل)
    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        # vignette vertical
        # أقتم في الأعلى والأسفل
        factor = abs(y - H/2) / (H/2) # 0 center, 1 edge
        alpha = int(70 * (factor ** 1.8))
        # لون أسود شفاف
        od.line([(0,y),(W,y)], fill=(0,0,0,alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # إضافة توهجات ذهبية ناعمة (مستقبلية)
    glow_layer = Image.new("RGBA", (W,H), (0,0,0,0))
    gdraw = ImageDraw.Draw(glow_layer)
    # توهج يسار ذهبي
    for cx, cy, rx, ry, col, alpha_base in [
        (280, H//2, 900, 700, (212,175,55), 28),
        (W-280, H//2, 900, 700, (212,175,55), 28),
        (W//2, H+180, 1400, 500, (212,175,55), 18),
        (W//2, -120, 1800, 400, (180, 190, 210), 14), # فضي علوي
        (W//2, H//2, 600, 600, (42, 60, 90), 22), # أزرق تكنولوجي خافت في المنتصف
    ]:
        # ارسم بيضاوي بتدرج شعاعي مبسط
        steps = 60
        for i in range(steps):
            r = 1 - i/steps
            alpha = int(alpha_base * (r ** 1.2) * 0.6)
            if alpha <=0: continue
            x0 = cx - rx*r
            y0 = cy - ry*r
            x1 = cx + rx*r
            y1 = cy + ry*r
            gdraw.ellipse([x0,y0,x1,y1], fill=(*col, alpha))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=35))
    img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")

    return img

def draw_honeycomb(img, opacity=22):
    layer = Image.new("RGBA", (W,H), (0,0,0,0))
    draw = ImageDraw.Draw(layer)
    # شبكة سداسية خفيفة جدا خلف اللوجو
    hex_r = 38
    hex_w = hex_r * 2
    hex_h = math.sqrt(3) * hex_r
    col = (58, 65, 78, opacity)
    # نرسم فقط في منطقة المنتصف والخلفية بشكل خافت
    for row in range(-2, int(H/hex_h)+3):
        for col_idx in range(-2, int(W/hex_w)+3):
            x = col_idx * hex_w + (hex_r if row %2 ==1 else 0) + W//2 - 600
            y = row * hex_h + H//2 - 320
            # تخطي البعيد جدا
            if abs(x - W//2) > 1100 and abs(y - H//2) > 350:
                continue
            points = []
            for i in range(6):
                ang = math.radians(30 + i*60)
                px = x + hex_r*0.87 * math.cos(ang)
                py = y + hex_r*0.87 * math.sin(ang)
                points.append((px, py))
            draw.polygon(points, outline=col, width=1)
    # خطوط دوائر تشبه اللوجو
    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.3))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return img

def draw_circuit_decor(img):
    layer = Image.new("RGBA", (W,H), (0,0,0,0))
    draw = ImageDraw.Draw(layer)
    gold = (212,175,55, 95)
    gold_light = (232,199,105, 70)
    silver = (170,178,190, 45)

    # خطوط علوية وسفلية رفيعة مع نقاط دوائر
    # خط ذهبي علوي
    y_top = 42
    y_bot = H-42
    # خط ذهبي علوي متدرج
    for w_line in [3,1]:
        alpha = 160 if w_line==3 else 90
        draw.line([(120, y_top),(W-120, y_top)], fill=(212,175,55, alpha), width=w_line)
        draw.line([(120, y_bot),(W-120, y_bot)], fill=(212,175,55, alpha), width=w_line)
    # خط فضي ثانوي
    draw.line([(140, y_top+9),(W-140, y_top+9)], fill=(170,178,190, 50), width=1)
    draw.line([(140, y_bot-9),(W-140, y_bot-9)], fill=(170,178,190, 50), width=1)

    # نقاط دوائر تشبه اللوجو على الجوانب
    def circuit_branch(x0,y0, direction=1, scale=1.0):
        # direction 1 = يمين, -1 = يسار
        pts = [
            (x0, y0),
            (x0+18*direction*scale, y0-14*scale),
            (x0+38*direction*scale, y0-14*scale),
            (x0+58*direction*scale, y0+8*scale),
            (x0+78*direction*scale, y0+8*scale),
        ]
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=gold, width=2)
        # نقاط
        for (px,py) in pts[1:]:
            draw.ellipse([px-7,py-7,px+7,py+7], fill=(12,14,18,255), outline=(212,175,55,180), width=2)
            draw.ellipse([px-3,py-3,px+3,py+3], fill=(232,199,105,220))
        # فروع صغيرة
        branch_pts = [(pts[1][0], pts[1][1]-12*scale), (pts[3][0], pts[3][1]+14*scale)]
        for bx,by in branch_pts:
            draw.line([(pts[1][0], pts[1][1]), (bx,by)], fill=gold_light, width=1)
            draw.ellipse([bx-6,by-6,bx+6,by+6], fill=(12,14,18,255), outline=(212,175,55,140), width=1)
            draw.ellipse([bx-2,by-2,bx+2,by+2], fill=(232,199,105,180))

    # زخارف علوية يمين ويسار
    circuit_branch(180, y_top, direction=1, scale=1.1)
    circuit_branch(W-180, y_top, direction=-1, scale=1.1)
    circuit_branch(180, y_bot, direction=1, scale=0.9)
    circuit_branch(W-180, y_bot, direction=-1, scale=0.9)

    # خطوط عمودية جانبية خفيفة
    for x in [90, W-90]:
        draw.line([(x, 95),(x, H-95)], fill=(212,175,55,35), width=1)
        draw.line([(x+12, 115),(x+12, H-115)], fill=(170,178,190,22), width=1)

    # أقواس ذهبية خفيفة حول المنتصف تشبه اللوجو
    # قوس علوي ذهبي
    arc_layer = Image.new("RGBA", (W,H), (0,0,0,0))
    ad = ImageDraw.Draw(arc_layer)
    # قوسين بيضاويين
    for offset, col, w in [( -8, (212,175,55,45), 4), (0, (232,199,105,28), 2), (8, (170,178,190,22),2)]:
        ad.arc([W//2-820+offset, 110+offset, W//2+820+offset, H+520+offset], start=200, end=340, fill=col, width=w)
        ad.arc([W//2-780+offset, -420+offset, W//2+780+offset, 720+offset], start=20, end=160, fill=col, width=w)
    arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(radius=1.2))
    layer = Image.alpha_composite(layer, arc_layer)

    # توهجات صغيرة متناثرة
    for (x,y, r) in [(460, 140, 3),(W-460,140,3),(520, H-140,2.5),(W-520,H-140,2.5), (W//2-620, H//2, 2), (W//2+620,H//2,2)]:
        draw.ellipse([x-r*3,y-r*3,x+r*3,y+r*3], fill=(212,175,55,60))
        draw.ellipse([x-r,y-r,x+r,y+r], fill=(255,240,180,210))

    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return img

def create_text_image(text, font, width, height, fill_type="gold"):
    # ننشئ صورة للنص مع تدرج ذهبي
    # نحسب bbox
    dummy = Image.new("RGBA", (width, height), (0,0,0,0))
    d = ImageDraw.Draw(dummy)
    # bbox
    bbox = d.textbbox((0,0), text, font=font)
    tw = bbox[2]-bbox[0]
    th = bbox[3]-bbox[1]
    # إنشاء صورة بحجم النص
    pad = 40
    img_w = tw + pad*2
    img_h = th + pad*2
    txt_img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
    txt_draw = ImageDraw.Draw(txt_img)
    # موضع النص في المنتصف
    x = pad - bbox[0]
    y = pad - bbox[1]
    # ظل عميق
    shadow_offset = 6 if fill_type=="gold_large" else 4
    txt_draw.text((x+shadow_offset, y+shadow_offset), text, font=font, fill=(0,0,0,190))
    txt_draw.text((x+shadow_offset+2, y+shadow_offset+2), text, font=font, fill=(0,0,0,110))
    # الآن نرسم النص بتدرج
    if fill_type in ("gold", "gold_large", "gold_small"):
        # ننشئ تدرج ذهبي عمودي للكتابة
        grad = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        gdraw = ImageDraw.Draw(grad)
        # تدرج ذهبي: من #8A6A0A -> #D4AF37 -> #FFD87A -> #D4AF37 -> #8A6A0A
        gold_stops = [(0.0,(138,106,10)), (0.22,(212,175,55)), (0.42,(255,226,130)), (0.55,(212,175,55)), (0.75,(184,142,26)), (1.0,(138,106,10))]
        for yy in range(img_h):
            t = yy / img_h
            for i in range(len(gold_stops)-1):
                p0,c0 = gold_stops[i]
                p1,c1 = gold_stops[i+1]
                if p0 <= t <= p1:
                    lt = (t-p0)/(p1-p0) if p1!=p0 else 0
                    c = lerp_color(c0,c1, lt)
                    gdraw.line([(0,yy),(img_w,yy)], fill=(*c,255))
                    break
        # قناع النص
        mask = Image.new("L", (img_w, img_h), 0)
        mdraw = ImageDraw.Draw(mask)
        # حد خارجي سميك للذهب البارز
        stroke_w = 10 if fill_type=="gold_large" else 6 if fill_type=="gold" else 4
        # نرسم النص على القناع مرتين: مرة للـ stroke ومرة للـ fill
        # stroke عبر رسم النص مع stroke_width
        mdraw.text((x,y), text, font=font, fill=255, stroke_width=stroke_w, stroke_fill=255)
        # نطبق التدرج عبر القناع
        # نحتاج إلى فصل الـ stroke بلون أغمق
        # ننشئ صورة للـ stroke فقط
        stroke_mask = Image.new("L", (img_w, img_h), 0)
        sdraw = ImageDraw.Draw(stroke_mask)
        sdraw.text((x,y), text, font=font, fill=255, stroke_width=stroke_w, stroke_fill=255)
        # نحفر الداخل لترك الحافة فقط
        inner_mask = Image.new("L", (img_w, img_h), 0)
        idraw = ImageDraw.Draw(inner_mask)
        idraw.text((x,y), text, font=font, fill=255)
        # edge = stroke - inner
        # بدل التعقيد، نرسم تدرج على كامل النص مع حافة غامقة
        # نركب التدرج
        txt_img2 = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        # الحافة الغامقة
        edge_color = (95, 72, 8, 255)  # بني ذهبي غامق
        # ارسم النص بالحافة
        edge_img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        ed = ImageDraw.Draw(edge_img)
        ed.text((x,y), text, font=font, fill=edge_color, stroke_width=stroke_w, stroke_fill=edge_color)
        # ادمج التدرج في الداخل
        # نستخدم mask الداخلي لقص التدرج
        inner_grad = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        inner_grad.paste(grad, (0,0), mask=inner_mask)
        # ركب الكل: الحافة + التدرج الداخلي
        txt_img2 = Image.alpha_composite(edge_img, inner_grad)
        # highlight علوي للذهب (لمعان)
        highlight = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        hdraw = ImageDraw.Draw(highlight)
        # لمعة بيضاء شفافة في الثلث العلوي من الحروف
        hdraw.text((x, y-1), text, font=font, fill=(255,255,240,90), stroke_width=0)
        # استخدم ماسك فقط للثلث العلوي
        # نقطع اللمعان بماسك متدرج
        alpha_grad = Image.new("L", (img_w, img_h), 0)
        for yy in range(img_h):
            # تدرج عمودي للشفافية: قوي في الأعلى يتلاشى في المنتصف
            rel = yy / img_h
            if rel < 0.45:
                a = int(255 * (1 - rel/0.45) * 0.7)
                ImageDraw.Draw(alpha_grad).line([(0,yy),(img_w,yy)], fill=a)
        highlight.putalpha(alpha_grad)
        temp = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        # نحتاج لتطبيق highlight فقط داخل الحروف
        highlight_masked = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        highlight_masked.paste(highlight, (0,0), mask=inner_mask)
        txt_img2 = Image.alpha_composite(txt_img2, highlight_masked)

        # ظل النص الأساسي كان مرسوم سابقا في txt_img، ندمجه
        base_with_shadow = txt_img
        # txt_img2 فوق الظل
        # نحتاج نحسب إزاحة لأن txt_img2 فيه pad
        result = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        result = Image.alpha_composite(result, base_with_shadow)
        result = Image.alpha_composite(result, txt_img2)
        return result
    elif fill_type == "silver_white":
        # نص فضي/أبيض لامع للعنوان الرئيسي
        # تدرج فضي أبيض
        grad = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        gdraw = ImageDraw.Draw(grad)
        silver_stops = [(0.0,(180,185,195)), (0.25,(240,242,245)), (0.5,(255,255,255)), (0.75,(220,225,235)), (1.0,(175,180,190))]
        for yy in range(img_h):
            t = yy / img_h
            for i in range(len(silver_stops)-1):
                p0,c0 = silver_stops[i]
                p1,c1 = silver_stops[i+1]
                if p0 <= t <= p1:
                    lt = (t-p0)/(p1-p0) if p1!=p0 else 0
                    c = lerp_color(c0,c1, lt)
                    gdraw.line([(0,yy),(img_w,yy)], fill=(*c,255))
                    break
        mask = Image.new("L", (img_w, img_h), 0)
        mdraw = ImageDraw.Draw(mask)
        stroke_w = 9
        mdraw.text((x,y), text, font=font, fill=255, stroke_width=stroke_w, stroke_fill=255)
        inner_mask = Image.new("L", (img_w, img_h), 0)
        ImageDraw.Draw(inner_mask).text((x,y), text, font=font, fill=255)
        edge_img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        ed = ImageDraw.Draw(edge_img)
        # حافة ذهبية للعنوان الرئيسي لربطه باللوجو
        edge_img_color = (130,110,30,255)
        ed.text((x,y), text, font=font, fill=edge_img_color, stroke_width=stroke_w, stroke_fill=edge_img_color)
        # تدرج ملون ثانوي ذهبي خفيف للحافة
        edge_glow = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        ImageDraw.Draw(edge_glow).text((x,y), text, font=font, fill=(212,175,55,120), stroke_width=stroke_w+4, stroke_fill=(212,175,55,60))
        edge_glow = edge_glow.filter(ImageFilter.GaussianBlur(radius=6))
        inner_grad = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        inner_grad.paste(grad, (0,0), mask=inner_mask)
        # highlight
        highlight = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        ImageDraw.Draw(highlight).text((x,y-1), text, font=font, fill=(255,255,255,60))
        alpha_grad = Image.new("L", (img_w, img_h), 0)
        for yy in range(img_h):
            rel = yy / img_h
            if rel < 0.5:
                a = int(180 * (1 - rel/0.5))
                ImageDraw.Draw(alpha_grad).line([(0,yy),(img_w,yy)], fill=a)
        highlight.putalpha(alpha_grad)
        highlight2 = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        highlight2.paste(highlight, (0,0), mask=inner_mask)

        result = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        # ظل
        shadow = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        ImageDraw.Draw(shadow).text((x+7,y+7), text, font=font, fill=(0,0,0,160), stroke_width=stroke_w, stroke_fill=(0,0,0,160))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        result = Image.alpha_composite(result, shadow)
        result = Image.alpha_composite(result, edge_glow)
        result = Image.alpha_composite(result, edge_img)
        result = Image.alpha_composite(result, inner_grad)
        result = Image.alpha_composite(result, highlight2)
        # لمعة ذهبية سفلية خفيفة
        return result
    else:
        txt_draw.text((x,y), text, font=font, fill=(255,255,255,255))
        return txt_img

def main():
    # الخلفية
    bg = create_background()
    bg = draw_honeycomb(bg, opacity=18)
    bg = draw_circuit_decor(bg)

    # اللوجو في المنتصف مع توهج
    logo = Image.open(LOGO_PATH).convert("RGBA")
    # اللوجو الأصلي 1024 تقريبا، نصغره لـ 420
    logo_size = 440
    # ظل وتوهج خلف اللوجو
    glow = Image.new("RGBA", (W,H), (0,0,0,0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = W//2, 455  # مركز اللوجو
    # توهج ذهبي خلف اللوجو
    for r, alpha in [(420, 35),(360, 45),(300, 55)]:
        gdraw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(212,175,55, alpha))
    # توهج فضي خفيف
    gdraw.ellipse([cx-250, cy-250, cx+250, cy+250], fill=(200,210,225, 18))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=28))
    bg_rgba = bg.convert("RGBA")
    bg_rgba = Image.alpha_composite(bg_rgba, glow)

    # حلقة ذهبية رفيعة حول اللوجو تشبه الهالة
    halo = Image.new("RGBA", (W,H), (0,0,0,0))
    hdraw = ImageDraw.Draw(halo)
    for w, alpha, rad in [(18, 22, 246),(6, 70, 238),(2, 120, 232)]:
        hdraw.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=(212,175,55, alpha), width=w)
    halo = halo.filter(ImageFilter.GaussianBlur(radius=1.5))
    bg_rgba = Image.alpha_composite(bg_rgba, halo)

    # لوجو مع ظل
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
    # ظل للوجو
    shadow_logo = Image.new("RGBA", (W,H), (0,0,0,0))
    # نرسم ظل بيضاوي تحت اللوجو
    sdraw = ImageDraw.Draw(shadow_logo)
    sdraw.ellipse([cx-190, cy+168, cx+190, cy+218], fill=(0,0,0,110))
    shadow_logo = shadow_logo.filter(ImageFilter.GaussianBlur(radius=14))
    bg_rgba = Image.alpha_composite(bg_rgba, shadow_logo)
    # لصق اللوجو
    lx = cx - logo_size//2
    ly = cy - logo_size//2
    bg_rgba.paste(logo, (lx, ly), logo)

    # إضافة لمعة علوية خفيفة على اللوجو (تأثير زجاجي)
    # لا داعي

    # النصوص
    # العنوان الرئيسي
    title_text_raw = "المركز الفني للإصلاح والصيانة"
    # بديل: المستخدم كتب "للاصلاح و الصيانة" بالألف بدون همزة، نوحد
    title_text = reshape(title_text_raw)

    # اختيار الخط وحجم يملأ العرض (استغلال المساحات)
    # نجرب حجم كبير
    # نريد العنوان يملأ ~82% من العرض
    target_w = int(W * 0.82)
    chosen_size = 165
    # نجرب قياس
    test_font = ImageFont.truetype(FONT_BOLD, chosen_size)
    dummy = Image.new("RGB", (100,100))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0,0), title_text, font=test_font)
    tw = bbox[2]-bbox[0]
    # تعديل حجمه ليملأ العرض
    # scale
    if tw != 0:
        scale = target_w / tw
        # نحد من التكبير المبالغ
        scale = min(scale, 1.18)
        scale = max(scale, 0.85)
        chosen_size = int(chosen_size * scale)
        # إعادة قياس مع حدود
        chosen_size = max(135, min(chosen_size, 195))
    # نستخدم Tajawal-Bold للعنوان، Cairo أيضا جيد لكن Tajawal أكثر سمك
    font_title = ImageFont.truetype(FONT_BOLD, chosen_size)
    # نستخدم Cairo للعنوان إذا أردنا وزن أثقل؟ Tajawal-Bold وزن ممتاز
    # نحاول Cairo Black لو موجود لكن Tajawal يكفي
    # أنشئ صورة النص بتأثير فضي/أبيض مع حافة ذهبية
    title_img = create_text_image(title_text, font_title, W, 320, fill_type="silver_white")
    # موضع العنوان في الأعلى
    tx = (W - title_img.width)//2
    ty = 78  # تحت الخط الذهبي العلوي
    # لكن لضبط أن يكون متمركز أفقياً تماماً
    bg_rgba = Image.alpha_composite(bg_rgba, Image.new("RGBA", (W,H), (0,0,0,0)))
    # نلصق العنوان مع محاذاة دقيقة
    tmp = Image.new("RGBA", (W,H), (0,0,0,0))
    tmp.paste(title_img, (tx, ty), title_img)
    bg_rgba = Image.alpha_composite(bg_rgba, tmp)

    # اسم الفني بالذهبي البارز
    name_raw = "م / حمدي سلمان"
    # المستخدم كتب "م/حمدي سا لمان " مع مسافة، نوحد
    name_text = reshape(name_raw)
    # حجم كبير يستغل المساحة تحت اللوجو
    font_name_size = 92
    font_name = ImageFont.truetype(FONT_BOLD, font_name_size)
    # قياس لضمان العرض
    bbox_n = ImageDraw.Draw(Image.new("RGB",(10,10))).textbbox((0,0), name_text, font=font_name)
    tw_n = bbox_n[2]-bbox_n[0]
    # نريد عرضه حوالي 42% من عرض البانر
    target_nw = int(W*0.42)
    if tw_n>0:
        s = target_nw / tw_n
        s = min(max(s, 0.9), 1.35)
        font_name_size = int(font_name_size * s)
        font_name = ImageFont.truetype(FONT_BOLD, font_name_size)
    name_img = create_text_image(name_text, font_name, W, 220, fill_type="gold_large")
    nx = (W - name_img.width)//2
    ny = cy + logo_size//2 + 24  # تحت اللوجو مباشرة
    tmp2 = Image.new("RGBA", (W,H), (0,0,0,0))
    tmp2.paste(name_img, (nx, ny), name_img)
    bg_rgba = Image.alpha_composite(bg_rgba, tmp2)

    # رقم التليفون
    phone_raw = "ت : 01014010183"
    # نحتاج reshape مع الحفاظ على الأرقام من اليسار لليمين
    # نستخدم نفس الدالة لكن الأرقام ستظل LTR بفضل bidi
    phone_text = reshape(phone_raw)
    font_phone_size = 68
    font_phone = ImageFont.truetype(FONT_BOLD, font_phone_size)
    phone_img = create_text_image(phone_text, font_phone, W, 180, fill_type="gold")
    px = (W - phone_img.width)//2
    py = ny + name_img.height - 18
    tmp3 = Image.new("RGBA", (W,H), (0,0,0,0))
    tmp3.paste(phone_img, (px, py), phone_img)
    bg_rgba = Image.alpha_composite(bg_rgba, tmp3)

    # إضافة شريط ذهبي رفيع تحت رقم الهاتف يضيف فخامة
    deco = Image.new("RGBA", (W,H), (0,0,0,0))
    dd = ImageDraw.Draw(deco)
    line_y = py + phone_img.height + 6
    # خط ذهبي متدرج في المنتصف
    line_w = 420
    lx1 = W//2 - line_w//2
    lx2 = W//2 + line_w//2
    # تدرج شفاف على الجوانب
    # نرسمه كتدرج عبر تدرج خطي
    for i in range(line_w):
        # alpha يتدرج من 0 في الأطراف إلى 255 في المنتصف
        dist = abs(i - line_w/2) / (line_w/2)
        alpha = int(220 * (1 - dist**1.6))
        dd.line([(lx1+i, line_y),(lx1+i, line_y+3)], fill=(212,175,55, alpha))
    # نقطتين في النهايات
    dd.ellipse([lx1-5, line_y-3, lx1+5, line_y+6], fill=(212,175,55, 180), outline=(255,240,180,90), width=1)
    dd.ellipse([lx2-5, line_y-3, lx2+5, line_y+6], fill=(212,175,55, 180), outline=(255,240,180,90), width=1)
    # جوهرة صغيرة في المنتصف
    dd.ellipse([W//2-7, line_y-4, W//2+7, line_y+7], fill=(12,14,18,255), outline=(212,175,55,220), width=2)
    dd.ellipse([W//2-3, line_y-1, W//2+3, line_y+4], fill=(255,240,180,255))
    deco = deco.filter(ImageFilter.GaussianBlur(radius=0.4))
    bg_rgba = Image.alpha_composite(bg_rgba, deco)

    # إضافة نص جانبي صغير يوحي بالاحترافية (اختياري) - "صيانة جميع الأجهزة الكهربائية"
    # نضعه بخط صغير رفيع تحت العنوان أو على الجوانب
    # نضعه كلمعة مستقبلية صغيرة بين العنوان واللوجو
    # نضيف سطر رفيع تحت العنوان
    sub_raw = "صيانة • إصلاح • تطوير  •  جميع الأجهزة الكهربائية والمنزلية"
    sub_text = reshape(sub_raw)
    font_sub_size = 34
    try:
        font_sub = ImageFont.truetype(FONT_CAIRO, font_sub_size)
    except:
        font_sub = ImageFont.truetype(FONT_BOLD, font_sub_size)
    # نقيس ونرسمه مباشرة بلون فضي خافت
    sub_dummy = ImageDraw.Draw(Image.new("RGB",(10,10)))
    bbox_s = sub_dummy.textbbox((0,0), sub_text, font=font_sub)
    sub_w = bbox_s[2]-bbox_s[0]
    sub_h = bbox_s[3]-bbox_s[1]
    sub_img = Image.new("RGBA", (sub_w+40, sub_h+20), (0,0,0,0))
    sd = ImageDraw.Draw(sub_img)
    sd.text((20 - bbox_s[0], 10 - bbox_s[1]), sub_text, font=font_sub, fill=(200,210,225,190), stroke_width=0)
    # ظل خفيف
    sub_img2 = Image.new("RGBA", (W,H), (0,0,0,0))
    sub_x = (W - sub_img.width)//2
    sub_y = ty + title_img.height - 12
    sub_img2.paste(sub_img, (sub_x, sub_y), sub_img)
    # نخفف حدته بفلتر خفيف
    bg_rgba = Image.alpha_composite(bg_rgba, sub_img2)

    # لمسات نهائية: vignette خفيفة على الحواف
    vignette = Image.new("RGBA", (W,H), (0,0,0,0))
    vd = ImageDraw.Draw(vignette)
    # إطار داخلي غامق
    for i in range(60):
        alpha = int(22 * (1 - i/60)**1.4)
        vd.rectangle([i,i,W-1-i, H-1-i], outline=(0,0,0, alpha))
    bg_rgba = Image.alpha_composite(bg_rgba, vignette)

    # قص الحواف بزوايا دائرية خفيفة (اختياري للطباعة بدون)
    # لا نقص

    final = bg_rgba.convert("RGB")
    final.save(OUTPUT, quality=95, dpi=(300,300))
    print(f"Saved {OUTPUT} size {final.size}")

    # نسخة مصغرة للمعاينة
    preview = final.resize((1600, int(1600*H/W)), Image.LANCZOS)
    preview.save(OUTPUT_PREVIEW, quality=92)
    print(f"Saved preview {OUTPUT_PREVIEW}")

    # نسخة إضافية بنسبة طباعة 3:1 مقصوصة قليلاً للعرض في المحل (اختياري)
    # نحفظ أيضا نسخة بدون الـ dpi العالي
    return OUTPUT

if __name__ == "__main__":
    main()
