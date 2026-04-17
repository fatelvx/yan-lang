"""
dream.py — 迷霧之境

一個沒有確定結局的夢。
言記得你每次來過。世界從你的記憶裡生長。

操作：WASD/方向鍵 移動  E 互動  T 說話  Q 離開
"""
import sys, os, math, random
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

import pygame
import yan.yan as y

# ─── 尺寸 & 基礎色 ───────────────────────────────────
W, H   = 800, 600
TILE   = 40
COLS   = W // TILE
ROWS   = H // TILE
WORLD  = "__dream__"

TEXT_C = (185, 185, 205)
DIM_C  = (85,  85, 115)
DOOR_C = (55,  55,  88)
DOOR_X = (88,  55, 118)

# ─── JOURNAL ─────────────────────────────────────────
def _now(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def _E():   return y._load_user_journal(WORLD)

def times_dreamed():
    return sum(1 for e in _E() if isinstance(e,list) and len(e)>=2
               and str(e[0])=='meet' and str(e[1])==WORLD)

def count_tag(tag: str):
    return sum(1 for e in _E() if isinstance(e,list) and len(e)>=4
               and str(e[0])=='note' and str(e[3])==tag)

def count_prefix(prefix: str):
    return sum(1 for e in _E() if isinstance(e,list) and len(e)>=4
               and str(e[0])=='note' and str(e[3]).startswith(prefix))

def last_said():
    for e in reversed(_E()):
        if isinstance(e,list) and len(e)>=4 and str(e[0])=='note':
            t=str(e[3])
            if t.startswith('said:'): return t[5:]
    return ''

def all_said():
    return [str(e[3])[5:] for e in _E()
            if isinstance(e,list) and len(e)>=4
            and str(e[0])=='note' and str(e[3]).startswith('said:')]

def jw(s):     y._append_user(WORLD, s)
def note(tag, conf=1.0): jw(f'(note "{WORLD}" "{_now()}" "{tag}" {conf})')
def record_said(msg):
    safe = msg.replace('"',"'").replace('\n',' ')
    note(f'said:{safe}', 0.9)

def yn_maybe(c): return random.random() < c

# ─── 故事碎片池 ──────────────────────────────────────
DREAM_PHRASES = [
    "你來這裡找什麼",     "也許你忘了",
    "門在那裡但你沒看見", "有人說過你的名字",
    "水裡有你的影子",     "花不記得自己的顏色",
    "也許這裡一直有你",   "出口不是你以為的那個",
    "你每次都走同一條路", "試著往別的方向",
    "他在等你但不說話",   "你知道",
    "也許這是假的",       "也許那是真的",
    "沒有差別",           "回頭",
    "繼續",               "忘了方向",
    "你說過什麼",         "我記得你說過",
    "這裡沒有答案",       "也許問題本身是出口",
    "……",                "…………",
    "你不是第一次",       "還有多少",
    "在那扇門後面",       "有什麼東西在動",
    "你看見了嗎",         "也許你沒看見",
    "它一直在這裡",       "你才是新來的",
    "夢不需要邏輯",       "但它記得",
    "你的腳步聲",         "我聽到了",
    "這扇門每次都不一樣", "也許是你不一樣",
    "水往下流但你往前",   "方向是相對的",
    "你叫什麼",           "你記得嗎",
]

# ─── 角色繪製 ─────────────────────────────────────────
def _blend(c1,c2,t):
    return tuple(int(a+(b-a)*t) for a,b in zip(c1,c2))

def draw_player(surf, tx, ty, t_ms):
    cx  = tx*TILE + TILE//2
    cy  = ty*TILE + TILE//2 - 2
    col = (200, 200, 222)
    at  = t_ms / 650
    lt  = t_ms / 420
    # head
    pygame.draw.circle(surf, col, (cx, cy-12), 9)
    # neck
    pygame.draw.rect(surf, col, (cx-2, cy-3, 4, 5))
    # body
    pygame.draw.polygon(surf, col,
        [(cx-8,cy-2),(cx+8,cy-2),(cx+6,cy+14),(cx-6,cy+14)])
    # arms (swing)
    la = (cx-16+int(math.sin(at)*3), cy+10+int(math.cos(at)*2))
    ra = (cx+16-int(math.sin(at)*3), cy+10+int(math.cos(at)*2))
    pygame.draw.line(surf, col, (cx-8, cy+2), la, 3)
    pygame.draw.line(surf, col, (cx+8, cy+2), ra, 3)
    # legs
    ll = (cx-5+int(math.sin(lt)*3), cy+24)
    rl = (cx+5-int(math.sin(lt)*3), cy+24)
    pygame.draw.line(surf, col, (cx-3, cy+14), ll, 3)
    pygame.draw.line(surf, col, (cx+3, cy+14), rl, 3)

def draw_shadow(surf, tx, ty, t_ms):
    cx  = tx*TILE + TILE//2
    cy  = ty*TILE + TILE//2 + int(math.sin(t_ms/800)*3)
    col = (38, 33, 62)
    # aura
    for r in (24, 17, 11):
        g = pygame.Surface((r*2+4,r*2+4), pygame.SRCALPHA)
        pygame.draw.ellipse(g, (68, 48, 108, 16), (0,0,r*2+4,r*2+4))
        surf.blit(g, (cx-r-2, cy-20-r-2))
    hdx = int(math.sin(t_ms/230)*1.5)
    hdy = int(math.cos(t_ms/340)*1.5)
    # head
    pygame.draw.ellipse(surf, col, (cx-9+hdx, cy-22+hdy, 18, 16))
    # glowing eyes
    ec = (110, 38, 58) if yn_maybe(0.85) else col
    pygame.draw.circle(surf, ec, (cx-3+hdx, cy-16+hdy), 2)
    pygame.draw.circle(surf, ec, (cx+3+hdx, cy-16+hdy), 2)
    # body
    pygame.draw.polygon(surf, col,
        [(cx-10,cy-6),(cx+10,cy-6),(cx+12,cy+16),(cx-12,cy+16)])
    # ragged hem
    for i in range(-12, 13, 4):
        h = random.randint(2, 8)
        pygame.draw.rect(surf, col, (cx+i-2, cy+16, 4, h))
    # arms (long)
    pygame.draw.line(surf, col, (cx-10,cy-2), (cx-17,cy+13), 2)
    pygame.draw.line(surf, col, (cx+10,cy-2), (cx+17,cy+13), 2)

def draw_child(surf, tx, ty, t_ms):
    cx  = tx*TILE + TILE//2
    cy  = ty*TILE + TILE//2 + 4 + int(math.sin(t_ms/600+1.2)*2)
    col  = (78, 145, 100)
    hcol = (88, 165, 113)
    # hair tufts
    for dx in (-6,0,6):
        pygame.draw.circle(surf, (52,108,72), (cx+dx, cy-22), 5)
    # head
    pygame.draw.circle(surf, hcol, (cx, cy-13), 10)
    # eyes
    pygame.draw.circle(surf, (26,55,36), (cx-3, cy-14), 2)
    pygame.draw.circle(surf, (26,55,36), (cx+3, cy-14), 2)
    # smile
    pygame.draw.arc(surf, (26,55,36), (cx-3,cy-12,6,4), math.pi, 2*math.pi, 1)
    # body
    pygame.draw.rect(surf, col, (cx-6, cy-3, 12, 12))
    # arms
    pygame.draw.line(surf, col, (cx-6,cy-1), (cx-11,cy+5), 2)
    pygame.draw.line(surf, col, (cx+6,cy-1), (cx+11,cy+5), 2)
    # legs
    pygame.draw.line(surf, col, (cx-3,cy+9), (cx-4,cy+18), 2)
    pygame.draw.line(surf, col, (cx+3,cy+9), (cx+4,cy+18), 2)

def draw_self(surf, tx, ty, t_ms, dreams=0):
    cx  = tx*TILE + TILE//2
    cy  = ty*TILE + TILE//2 - 2 + int(math.sin(t_ms/1200)*1)
    r0  = max(70, 160 - dreams*5)
    col = (r0, r0+20, 215)
    # glow
    for rad in (22, 15, 9):
        g = pygame.Surface((rad*2, rad*2), pygame.SRCALPHA)
        pygame.draw.circle(g, (*col, 12), (rad,rad), rad)
        surf.blit(g, (cx-rad, cy-12-rad))
    # head
    pygame.draw.circle(surf, col, (cx, cy-12), 9)
    pygame.draw.rect(surf, col, (cx-2,cy-3,4,5))
    # body
    pygame.draw.polygon(surf, col,
        [(cx-8,cy-2),(cx+8,cy-2),(cx+6,cy+14),(cx-6,cy+14)])
    # arms (outstretched — slightly unnerving)
    pygame.draw.line(surf, col, (cx-8,cy+2), (cx-18,cy+9), 3)
    pygame.draw.line(surf, col, (cx+8,cy+2), (cx+18,cy+9), 3)
    # legs
    pygame.draw.line(surf, col, (cx-3,cy+14), (cx-5,cy+24), 3)
    pygame.draw.line(surf, col, (cx+3,cy+14), (cx+5,cy+24), 3)

def draw_reflection(surf, tx, ty, t_ms):
    cx  = tx*TILE + TILE//2
    cy  = ty*TILE + TILE//2 - 2
    col = (58, 88, 132)
    wv  = lambda i: int(math.sin(t_ms/250+i*0.8)*2)
    for r2 in range(9,0,-3):
        c2 = _blend(col, (8,12,22), r2/9)
        pygame.draw.circle(surf, c2, (cx+wv(r2), cy-12), r2)
    for i in range(4):
        pygame.draw.rect(surf, col, (cx-6+wv(i), cy-2+i*4, 12, 3))
    pygame.draw.line(surf, col, (cx-6+wv(0), cy), (cx-12+wv(1), cy+8), 2)
    pygame.draw.line(surf, col, (cx+6+wv(0), cy), (cx+12+wv(1), cy+8), 2)

def draw_light(surf, tx, ty, t_ms):
    cx = tx*TILE + TILE//2
    cy = ty*TILE + TILE//2
    pulse  = abs(math.sin(t_ms/390))*0.65+0.35
    base_r = int(13*pulse)
    col    = (222, 210, 170)
    for r2 in range(base_r*4, base_r, -4):
        a = max(0, 38-(base_r*4-r2)*3)
        g = pygame.Surface((r2*2,r2*2), pygame.SRCALPHA)
        pygame.draw.circle(g, (*col,a), (r2,r2), r2)
        surf.blit(g, (cx-r2, cy-r2))
    pygame.draw.circle(surf, col, (cx,cy), base_r)
    pygame.draw.circle(surf, (244,236,202), (cx,cy), max(1,base_r-4))

def draw_wanderer(surf, tx, ty, t_ms):
    cx   = tx*TILE + TILE//2
    cy   = ty*TILE + TILE//2 - 2 + int(math.sin(t_ms/700+2.5)*2)
    col  = (116, 90, 60)
    skin = (155, 128, 98)
    hat  = (78, 58, 38)
    pygame.draw.ellipse(surf, hat, (cx-13,cy-26,26,7))
    pygame.draw.rect(surf, hat, (cx-7,cy-34,14,10))
    pygame.draw.circle(surf, skin, (cx,cy-18), 8)
    pygame.draw.polygon(surf, col,
        [(cx-9,cy-8),(cx+7,cy-8),(cx+5,cy+14),(cx-7,cy+14)])
    pygame.draw.rect(surf, (92,72,48), (cx+5,cy-5,9,14))
    pygame.draw.line(surf, col, (cx-9,cy-3), (cx-14,cy+9), 3)
    pygame.draw.line(surf, col, (cx+7,cy-3), (cx+11,cy+5), 3)
    pygame.draw.line(surf, (98,78,52), (cx+11,cy+5), (cx+13,cy+23), 2)
    lt = t_ms/500
    pygame.draw.line(surf, col, (cx-3,cy+14), (cx-5+int(math.sin(lt)*2),cy+24), 3)
    pygame.draw.line(surf, col, (cx+2,cy+14), (cx+4-int(math.sin(lt)*2),cy+24), 3)

NPC_DRAW = {
    'shadow':     draw_shadow,
    'child':      draw_child,
    'reflection': draw_reflection,
    'light':      draw_light,
    'wanderer':   draw_wanderer,
}

# ─── 浮動文字 ─────────────────────────────────────────
class FloatText:
    def __init__(self, text, x, y, color, life=380):
        self.text = text
        self.x, self.y = float(x), float(y)
        self.vx   = random.uniform(-0.10, 0.10)
        self.vy   = random.uniform(-0.25, -0.05)
        self.peak = random.randint(40, 105)
        self.life = life
        self.age  = 0
        self.col  = color

    @property
    def alive(self): return self.age < self.life

    def update(self):
        self.x += self.vx; self.y += self.vy; self.age += 1

    def alpha(self):
        h = self.life // 2
        return int(self.peak * self.age / h) if self.age < h \
               else int(self.peak * (self.life-self.age) / h)

    def draw(self, surf, font_s):
        a = self.alpha()
        if a <= 0: return
        t  = font_s.render(self.text, True, self.col)
        ts = pygame.Surface(t.get_size(), pygame.SRCALPHA)
        ts.fill((0,0,0,0)); ts.blit(t,(0,0)); ts.set_alpha(a)
        surf.blit(ts, (int(self.x), int(self.y)))

_floats: list = []
_spawn_cd = 0

def _spawn_float(room, dreams):
    global _floats, _spawn_cd
    _spawn_cd -= 1
    if _spawn_cd > 0: return
    _spawn_cd = random.randint(55, 150)
    if not yn_maybe(0.60): return
    phrase = random.choice(DREAM_PHRASES)
    rc = room.get('color', (10,10,20))
    col = tuple(min(255, c+75+random.randint(0,55)) for c in rc)
    _floats.append(FloatText(phrase,
        random.randint(25, W-80), random.randint(H//3, H*2//3),
        col, random.randint(230,460)))

def _update_floats(surf, font_s):
    global _floats
    _floats = [f for f in _floats if f.alive]
    for f in _floats:
        f.update(); f.draw(surf, font_s)

# ─── 粒子 ─────────────────────────────────────────────
class Particle:
    def __init__(self): self._r()
    def _r(self):
        self.x  = random.uniform(0,W)
        self.y  = random.uniform(0,H)
        self.vx = random.uniform(-0.12,0.12)
        self.vy = random.uniform(-0.28,-0.05)
        self.a  = random.randint(8,42)
        self.sz = random.choice([1,1,2])
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.a-=0.15
        if self.y<-2 or self.a<=0 or not 0<=self.x<=W: self._r()
    def draw(self, surf):
        if self.a<=0: return
        s=pygame.Surface((self.sz*2,self.sz*2),pygame.SRCALPHA)
        s.fill((200,200,230,int(self.a))); surf.blit(s,(int(self.x),int(self.y)))

_PARTS = [Particle() for _ in range(60)]

# ─── 世界 ─────────────────────────────────────────────
ROOMS: dict = {
    'entrance': {
        'name':  '入口',
        'color': (12,12,22),
        'exits': {'n':'corridor','e':'garden'},
        'npcs':  [{'id':'shadow','x':5,'y':4}],
        'objs':  [
            {'id':'mirror','x':3, 'y':3,'ch':'▣','col':(80,80,120)},
            {'id':'frame', 'x':16,'y':9,'ch':'◻','col':(40,40,65)},
        ],
    },
    'corridor': {
        'name':  '走廊',
        'color': (8,8,18),
        'exits': {'s':'entrance','n':'depths'},
        'npcs':  [],
        'objs':  [
            {'id':'rune_l','x':2, 'y':4,'ch':'║','col':(30,30,50)},
            {'id':'rune_r','x':17,'y':4,'ch':'║','col':(30,30,50)},
            {'id':'seal',  'x':10,'y':7,'ch':'⊞','col':(45,45,70)},
        ],
    },
    'garden': {
        'name':  '霧中花園',
        'color': (8,16,12),
        'exits': {'w':'entrance'},
        'npcs':  [{'id':'child','x':8,'y':5}],
        'objs':  [
            {'id':'flower', 'x':5, 'y':3, 'ch':'✿','col':(50,90,55)},
            {'id':'flower2','x':13,'y':6, 'ch':'✾','col':(38,75,42)},
            {'id':'flower3','x':4, 'y':10,'ch':'❀','col':(58,98,60)},
            {'id':'stone',  'x':10,'y':8, 'ch':'○','col':(48,58,52)},
            {'id':'leaf',   'x':16,'y':3, 'ch':'◈','col':(30,48,32)},
        ],
    },
    'depths': {
        'name':  '最深處',
        'color': (4,4,14),
        'exits': {'s':'corridor'},
        'npcs':  [{'id':'self','x':10,'y':5}],
        'objs':  [
            {'id':'orb', 'x':4, 'y':3,'ch':'◎','col':(58,52,82)},
            {'id':'orb2','x':16,'y':9,'ch':'◎','col':(52,48,78)},
            {'id':'line','x':10,'y':2,'ch':'⋮','col':(35,30,55)},
        ],
    },
    'void': {
        'name':    '虛空',
        'color':   (0,0,4),
        'exits':   {'w':'corridor'},
        'npcs':    [{'id':'light','x':10,'y':7}],
        'objs':    [],
        'special': 'void',
    },
    'water': {
        'name':    '水面之上',
        'color':   (6,10,20),
        'exits':   {'s':'garden'},
        'npcs':    [{'id':'reflection','x':7,'y':3}],
        'objs':    [
            {'id':'reed', 'x':3, 'y':5,'ch':'∤','col':(38,58,48)},
            {'id':'reed2','x':16,'y':7,'ch':'∤','col':(34,52,44)},
            {'id':'lily', 'x':10,'y':4,'ch':'◌','col':(38,62,52)},
        ],
        'special': 'water',
    },
    'attic': {
        'name':  '閣樓',
        'color': (22,18,12),
        'exits': {'e':'depths'},
        'npcs':  [{'id':'wanderer','x':6,'y':6}],
        'objs':  [
            {'id':'chest','x':14,'y':4,'ch':'▪','col':(80,65,45)},
            {'id':'book', 'x':3, 'y':3,'ch':'▬','col':(70,55,40)},
            {'id':'lamp', 'x':17,'y':9,'ch':'⊙','col':(100,85,55)},
        ],
    },
    'shore': {
        'name':    '某個岸邊',
        'color':   (10,12,18),
        'exits':   {'n':'void'},
        'npcs':    [],
        'objs':    [
            {'id':'shell', 'x':5, 'y':9, 'ch':'◑','col':(75,72,62)},
            {'id':'shell2','x':12,'y':10,'ch':'◐','col':(70,68,58)},
            {'id':'drift', 'x':8, 'y':4, 'ch':'∼','col':(45,55,70)},
            {'id':'bottle','x':15,'y':7, 'ch':'⬡','col':(55,65,80)},
        ],
        'special': 'shore',
    },
}

def _grow_exits(dreams: int):
    vc = count_tag

    if vc('visit:corridor') >= 3 and 'e' not in ROOMS['corridor']['exits']:
        ROOMS['corridor']['exits']['e'] = 'void'

    if vc('visit:garden') >= 4 and 'n' not in ROOMS['garden']['exits']:
        ROOMS['garden']['exits']['n'] = 'water'

    if vc('visit:depths') >= 2 and 'w' not in ROOMS['depths']['exits']:
        ROOMS['depths']['exits']['w'] = 'attic'

    # 虛空 → 岸邊：每次進入有 40% 機率解鎖（本局固定後）
    if vc('visit:void') >= 1 and 's' not in ROOMS['void']['exits']:
        if yn_maybe(0.40):
            ROOMS['void']['exits']['s'] = 'shore'

    # 夢境碎片：由 said 數觸發
    if count_prefix('said:') >= 3 and 'shard_a' not in ROOMS:
        _gen_shard('shard_a', 'entrance', 'w', seed=dreams*7 + count_prefix('said:')*3)

    # 夢境碎片：由 talk 數觸發
    if count_prefix('talk:') >= 8 and 'shard_b' not in ROOMS:
        _gen_shard('shard_b', 'water', 'e', seed=dreams*11 + count_prefix('talk:')*5)

def _gen_shard(sid: str, parent: str, direction: str, seed: int):
    rng  = random.Random(seed)
    opp  = {'n':'s','s':'n','e':'w','w':'e'}
    base = tuple(rng.randint(0,14) for _ in range(3))
    tint = tuple(rng.randint(0,18) for _ in range(3))
    col  = tuple(min(255,a+b) for a,b in zip(base,tint))
    chars = ['○','◎','◈','⋮','▪','◐','◑','∼','⬡','◻','⊞','✿','∤','⋯','◆']
    objs  = []
    for i in range(rng.randint(2,5)):
        objs.append({
            'id':  f'{sid}_o{i}',
            'x':   rng.randint(2, COLS-3),
            'y':   rng.randint(2, ROWS-3),
            'ch':  rng.choice(chars),
            'col': tuple(rng.randint(28,95) for _ in range(3)),
        })
    names = ['裂縫','折疊的地方','某個空白','沒有名字','在另一側','記憶的縫隙','深一層']
    npcs  = []
    if rng.random() < 0.45:
        npc_t = rng.choice(['shadow','child','light'])
        npcs  = [{'id':npc_t,'x':rng.randint(3,COLS-4),'y':rng.randint(3,ROWS-4)}]
    ROOMS[sid] = {
        'name':    rng.choice(names),
        'color':   col,
        'exits':   {opp[direction]: parent},
        'npcs':    npcs,
        'objs':    objs,
        'special': 'shard',
    }
    ROOMS[parent]['exits'][direction] = sid

# ─── NPC 對話 ─────────────────────────────────────────
def get_dialogue(nid: str, state) -> str:
    talks  = count_tag(f'talk:{nid}')
    dreams = state.dreams
    said   = last_said()
    sall   = all_said()

    if nid == 'shadow':
        if talks == 0: return "……"
        if talks == 1: return "你又來了。"
        if talks == 2: return "這裡沒有出口。"
        if talks == 3: return "也許有。"
        if talks < 9:
            if said and yn_maybe(0.6):
                return f"你說過「{said[:14]}」。我記得。"
            return random.choice([
                "我在等你說話。","……",
                "你站在哪裡，你知道嗎。",
                "每次你進來，空氣就不一樣了。",
                "你不必解釋。","也許你本來就在這裡。",
            ])
        if dreams > 8:
            return random.choice(["你是我嗎。","我不確定了。","繼續走吧。","……"])
        return random.choice([
            "你每次都來找我。","我不會離開。","你也不會。",
            "我們都是這裡的一部分。",f"你來了 {dreams} 次。我知道。",
        ])

    if nid == 'child':
        if talks == 0: return "你找到這裡了。"
        if talks == 1: return "花已經不記得自己的顏色了。"
        if talks == 2: return "我也是。"
        if talks < 7:
            if said and yn_maybe(0.65):
                return f"我聽到你說的了。「{said[:12]}」。"
            return random.choice([
                "你帶種子來了嗎。","這裡以前有聲音的。",
                "我一直在這裡。","你怎麼知道這裡有花。",
                "花是記得你的，就算它不說。",
            ])
        return random.choice([
            "也許你是花。","也許我是你。","這沒關係的。",
            f"你來了 {dreams} 次了。花都記得。",
            "你還會回來嗎。","我不知道你去哪。但你會回來。",
        ])

    if nid == 'self':
        if talks == 0: return "你是第幾次來了？"
        if talks == 1: return f"第 {dreams} 次。我數過了。"
        if talks == 2: return "你認識自己嗎。"
        if talks == 3: return "我也不確定。"
        if talks < 8:
            if said and yn_maybe(0.7):
                return f"「{said[:16]}」—— 這是你說的。你還記得為什麼嗎。"
            if sall and yn_maybe(0.3):
                return f"你曾說過「{random.choice(sall)[:12]}」。那時候你在想什麼。"
            return random.choice([
                "你每次都不一樣。","也許這才是你。",
                f"來了 {dreams} 次還沒找到答案。",
                "繼續走吧。","我也在找。","也許答案不在這裡。",
            ])
        if dreams > 8:
            return random.choice([
                "你是我嗎。","我是你嗎。","這不重要了。",
                "我們都不需要答案。","……",
            ])
        return random.choice([
            "繼續走吧。","也許最深處不在這裡。","我等你再來。",
            f"第 {dreams} 次。你知道的。",
        ])

    if nid == 'reflection':
        if talks == 0: return "水裡的人不說話。"
        if talks == 1: return "他在看你。"
        if talks < 5:
            if said and yn_maybe(0.6):
                return f"水裡的聲音：「{said[:12]}」"
            return random.choice([
                "水面很安靜。","他走到哪裡，我就在哪裡。",
                "你比我清楚你是誰嗎。","也許不是。",
            ])
        return random.choice([
            "我比你更清楚你是誰。","你走到哪裡我就在哪裡。",
            "……","水不說謊。","它只是映照。",
        ])

    if nid == 'light':
        if talks == 0: return "這裡什麼都沒有。"
        if talks == 1: return "但你來了。"
        if talks < 6:
            if said and yn_maybe(0.55):
                return f"「{said[:12]}」在黑暗裡迴盪。"
            return random.choice([
                "你不會迷路的。","也許你本來就在這裡。","虛空不是空的。",
                "它只是很安靜。","我也不知道出口在哪。",
            ])
        return random.choice([
            "你的記憶讓這裡有了形狀。","每次你來，這裡就多一點什麼。",
            "……","光是你帶來的。","也許光從來就在。",
        ])

    if nid == 'wanderer':
        if talks == 0: return "我在找一個地方。"
        if talks == 1: return "你知道路嗎。"
        if talks == 2: return "我也不確定我在找什麼。"
        if talks < 6:
            if said and yn_maybe(0.5):
                return f"你說「{said[:12]}」。也許那是出口的名字。"
            return random.choice([
                "走了很久了。","還有多遠我不知道。",
                "你也是在走嗎。","也許方向本身是個錯誤。",
                "我帶了些東西，但不記得是什麼了。",
            ])
        return random.choice([
            "也許我一直走就對了。","你有找到什麼嗎。",
            "我在等一個感覺。","……",
            "你先走吧。我還在這裡一會兒。",
        ])

    return "……"

# ─── 物件互動 ─────────────────────────────────────────
def handle_obj(obj_id: str, state):
    touches = count_tag(f'touch:{obj_id}')
    said    = last_said()
    vc      = count_tag

    _lines = {
        'mirror':  [
            "你看到了自己，或者你以為你看到了。",
            f"來過 {state.dreams} 次的人。你認識他嗎。",
            f"鏡裡的人說：「{said[:14]}」" if said else "鏡子在等你說話。",
            "你認識那個人嗎。","鏡子是空的。","你和它都不說話。",
        ],
        'frame':   ["拱框沒有鑲什麼。","也許曾經有。","框本身或許就是全部。"],
        'flower':  ["花是真實的。也許。","你又碰了它。它還在。",
                    f"花摸了 {touches} 次。","你伸手，什麼都沒有了。"],
        'flower2': ["這朵也是。","它長在這裡很久了。","你碰了它。也許它感覺到了。"],
        'flower3': ["還有這朵。","花的名字已經不重要了。","它不需要名字才能存在。"],
        'stone':   ["石頭很沉。","石頭在這裡已經很久了。","比你更久。","比任何名字更久。"],
        'leaf':    ["一片葉子。","它停在這裡。","也許風帶來的。也許不是。"],
        'seal':    [f"符文在等 visit 累積。",
                    f"走廊走了 {vc('visit:corridor')} 次。",
                    "符號有時候只是符號。"],
        'rune_l':  ["柱子。","它撐著什麼你不確定。","也許什麼都沒有。"],
        'rune_r':  ["還有一根。","對稱讓人安心。","也許只是習慣。"],
        'orb':     [f"光球幾乎不發光。",f"此處來了 {vc('visit:depths')} 次。"],
        'orb2':    ["另一個。","它比你更安靜。"],
        'line':    ["一條線。","它指向哪裡你不確定。","也許哪裡都不是。"],
        'reed':    ["蘆葦在水裡的倒影更真實。","沙沙。","它一直在這裡。"],
        'reed2':   ["另一根蘆葦。","水在它周圍。","它習慣了。"],
        'lily':    ["睡蓮浮在水面。","它不屬於水，也不屬於天空。","它浮著。"],
        'chest':   ["箱子是鎖著的。",
                    f"也許裡面有你說過的話——「{said[:18]}」" if said else "也許裡面是空的。",
                    "你沒有打開它。"],
        'book':    ["書沒有標題。","也許裡面是空的。","也許你不應該看。"],
        'lamp':    ["燈沒有開。",f"也許有 {state.dreams} 個原因。","你沒有找到開關。"],
        'shell':   ["貝殼。","你把它靠近耳朵。什麼都沒有。","也許需要再近一點。"],
        'shell2':  ["另一個。","它更小。也許聲音更清楚。","還是什麼都沒有。"],
        'drift':   ["漂來的什麼。","它沒有名字。","你給它名字它也不知道。"],
        'bottle':  ["瓶子是空的。","也許曾有東西在裡面。","也許沒有。"],
    }

    pool = _lines.get(obj_id)
    if pool is None:
        # 程序生成房間裡的物件
        pool = ["……","它在這裡。","你觸碰了它。",
                "也許它有意義。也許沒有。",
                f"這是第 {touches+1} 次碰它。"]

    idx = min(touches, len(pool)-1)
    state.say(pool[idx] if not yn_maybe(0.22) else random.choice(pool))
    note(f'touch:{obj_id}')

# ─── 遊戲狀態 ─────────────────────────────────────────
class GameState:
    def __init__(self):
        self.room_id     = 'entrance'
        self.px, self.py = COLS//2, ROWS//2
        self.dialogue    = None
        self.dlg_timer   = 0
        self.visited     = set()
        self.dreams      = times_dreamed()
        self.fog         = max(0.10, 1.0 - self.dreams*0.055)
        self.fade_a      = 255
        self.fading      = False
        self.fade_dest   = None
        self.fade_pos    = (COLS//2, ROWS//2)
        self._done_enter = False
        self.input_mode  = False
        self.input_text  = ''
        self._blink      = 0

    @property
    def room(self): return ROOMS[self.room_id]

    def enter_room(self, rid, pos=None):
        self.room_id = rid
        self.visited.add(rid)
        note(f'visit:{rid}')
        _grow_exits(self.dreams)
        self.px, self.py = pos if pos else (COLS//2, ROWS//2)

    def go(self, dest, pos):
        if self.fading: return
        self.fading, self.fade_dest, self.fade_pos = True, dest, pos
        self._done_enter = False

    def say(self, text, dur=215):
        self.dialogue, self.dlg_timer = text, dur

    def tick(self):
        if self.dlg_timer > 0:
            self.dlg_timer -= 1
            if self.dlg_timer == 0: self.dialogue = None
        self._blink = (self._blink+1) % 60
        if self.fading:
            self.fade_a = min(255, self.fade_a+20)
            if self.fade_a >= 255 and not self._done_enter:
                self._done_enter = True
                self.enter_room(self.fade_dest, self.fade_pos)
                self.fading = False
        else:
            self.fade_a = max(0, self.fade_a-15)

    def busy(self): return self.fading or self.fade_a > 40

# ─── 渲染 ─────────────────────────────────────────────
def draw_room(surf, state, font_s):
    room    = state.room
    special = room.get('special')
    t_ms    = pygame.time.get_ticks()

    surf.fill(room['color'])

    if   special == 'void':  _draw_void(surf)
    elif special == 'water': _draw_water(surf)
    elif special == 'shore': _draw_shore(surf)
    elif special == 'shard': _draw_shard_bg(surf, room)
    else: _draw_tiles(surf, room['color'])

    # 物件
    for obj in room.get('objs', []):
        tc   = count_tag(f'touch:{obj["id"]}')
        conf = min(0.96, 0.42+tc*0.10) + random.uniform(-0.06, 0.06)
        if yn_maybe(conf):
            t = font_s.render(obj['ch'], True, obj['col'])
            surf.blit(t, t.get_rect(center=(obj['x']*TILE+TILE//2, obj['y']*TILE+TILE//2)))

    # NPC
    for npc in room.get('npcs', []):
        nid = npc['id']
        if nid == 'self':
            draw_self(surf, npc['x'], npc['y'], t_ms, state.dreams)
        elif nid in NPC_DRAW:
            NPC_DRAW[nid](surf, npc['x'], npc['y'], t_ms)

    # 玩家
    draw_player(surf, state.px, state.py, t_ms)

    # 水面倒影（玩家）
    if special == 'water':
        wy  = ROWS//2*TILE
        py_ = state.py*TILE + TILE//2
        ry  = wy + (wy-py_)
        rip = int(math.sin(t_ms/300)*2)
        s   = pygame.Surface((TILE,TILE), pygame.SRCALPHA)
        pygame.draw.rect(s, (200,200,222,35), (6,rip+4,TILE-12,TILE-8))
        surf.blit(s, (state.px*TILE, ry-TILE//2))

    # 出口標記
    exits = room.get('exits',{})
    shard_ids = {k for k in ROOMS if 'shard' in k}
    mystery = {'void','attic','shore'} | shard_ids
    for d,(rx,ry,rw,rh) in {
        'n':(W//2-20,0,40,5),'s':(W//2-20,H-5,40,5),
        'e':(W-5,H//2-20,5,40),'w':(0,H//2-20,5,40),
    }.items():
        if d in exits:
            col = DOOR_X if exits[d] in mystery else DOOR_C
            pygame.draw.rect(surf, col, (rx,ry,rw,rh))

    # 霧氣
    fog_s = pygame.Surface((W,H), pygame.SRCALPHA)
    op    = int(state.fog*82)
    for i in range(0,W,6):
        for j in range(0,H,6):
            if random.random() < state.fog*0.009:
                fog_s.fill((0,0,0,op),(i,j,6,6))
    surf.blit(fog_s,(0,0))

    # 粒子 & 浮動文字
    for p in _PARTS: p.update(); p.draw(surf)
    _spawn_float(room, state.dreams)
    _update_floats(surf, font_s)

def _draw_tiles(surf, base):
    for r in range(ROWS):
        for c in range(COLS):
            if (r+c)%2==0:
                s = pygame.Surface((TILE,TILE), pygame.SRCALPHA)
                s.fill((*[min(255,x+8) for x in base],22))
                surf.blit(s,(c*TILE,r*TILE))

def _draw_void(surf):
    t_s = pygame.time.get_ticks()/1000.0
    rng = random.Random(42)
    for _ in range(240):
        sx=rng.randint(0,W); sy=rng.randint(0,H)
        bri=rng.randint(20,88); spd=rng.uniform(0.3,2.4); phi=rng.uniform(0,6.28)
        a=int(bri*abs(math.sin(t_s*spd+phi)))
        s=pygame.Surface((2,2),pygame.SRCALPHA); s.fill((bri,bri,bri+12,a))
        surf.blit(s,(sx,sy))

def _draw_water(surf):
    t_s = pygame.time.get_ticks()/1000.0
    wy  = ROWS//2*TILE
    for row in range(ROWS//2, ROWS):
        a = 15+int(7*math.sin(t_s*1.3+row*0.25))
        s = pygame.Surface((W,TILE),pygame.SRCALPHA); s.fill((24,40,70,a))
        surf.blit(s,(0,row*TILE))
    pygame.draw.line(surf,(25,44,82),(0,wy),(W,wy),2)

def _draw_shore(surf):
    t_s = pygame.time.get_ticks()/1000.0
    for i in range(5):
        y = ROWS*TILE*2//3+i*18+int(math.sin(t_s+i*0.5)*4)
        a = max(0, 34-i*6)
        s = pygame.Surface((W,2),pygame.SRCALPHA); s.fill((52,68,98,a))
        surf.blit(s,(0,y))

def _draw_shard_bg(surf, room):
    col = room['color']
    t_s = pygame.time.get_ticks()/1000.0
    for i in range(8):
        x = int(W//2+math.cos(t_s*0.3+i*0.78)*200)
        y = int(H//2+math.sin(t_s*0.4+i*0.78)*150)
        r = int(30+math.sin(t_s*0.5+i)*20)
        c = tuple(min(255,v+18+(i*5)) for v in col)
        s = pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*c,14),(r,r),r)
        surf.blit(s,(x-r,y-r))

def draw_ui(surf, state, font, font_s):
    room = state.room
    name = room['name']
    if state.dreams > 5 and yn_maybe(0.13): name = '…'
    surf.blit(font_s.render(name, True, DIM_C), (12,12))
    nt = font_s.render(f"第 {state.dreams} 夜", True, (40,40,60))
    surf.blit(nt, (W-nt.get_width()-12, 12))

    ht = font_s.render("WASD 移動  E 互動  T 說話  Q 離開", True, (28,28,44))
    surf.blit(ht, (W//2-ht.get_width()//2, H-18))

    if state.dialogue:
        bh  = 90
        btp = H-bh-22
        bx  = pygame.Surface((W,bh),pygame.SRCALPHA)
        bx.fill((0,0,8,215)); surf.blit(bx,(0,btp))
        text = state.dialogue
        if state.dreams > 9 and yn_maybe(0.09):
            text = ''.join(c if random.random()>0.07 else '·' for c in text)
        rnd = font.render(text, True, TEXT_C)
        if rnd.get_width() > W-40:
            mid = len(text)//2
            surf.blit(font.render(text[:mid],True,TEXT_C),(20,btp+12))
            surf.blit(font.render(text[mid:],True,TEXT_C),(20,btp+46))
        else:
            surf.blit(rnd,(20,btp+30))

def draw_input(surf, state, font, font_s):
    bh = 100
    bx = pygame.Surface((W,bh),pygame.SRCALPHA)
    bx.fill((3,3,16,238)); surf.blit(bx,(0,H-bh))
    surf.blit(font_s.render("說：",True,(75,75,105)),(20,H-bh+12))
    cur = '|' if state._blink<30 else ' '
    surf.blit(font.render(state.input_text+cur,True,TEXT_C),(20,H-bh+36))
    surf.blit(font_s.render("Enter 確認  Esc 取消",True,(36,36,56)),(W-165,H-bh+76))

def draw_fade(surf, state):
    if state.fade_a > 0:
        s = pygame.Surface((W,H)); s.set_alpha(state.fade_a); surf.blit(s,(0,0))

# ─── 互動輔助 ─────────────────────────────────────────
def near_npc(state):
    for npc in state.room.get('npcs',[]):
        if abs(npc['x']-state.px)<=1 and abs(npc['y']-state.py)<=1: return npc
    return None

def near_obj(state):
    for obj in state.room.get('objs',[]):
        if abs(obj['x']-state.px)<=1 and abs(obj['y']-state.py)<=1: return obj
    return None

# ─── 主程式 ──────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W,H))
    pygame.display.set_caption('迷霧之境')
    clock  = pygame.time.Clock()

    font_path = next((p for p in [
        'C:/Windows/Fonts/msjh.ttc','C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simsun.ttc',
    ] if os.path.exists(p)), None)
    font   = pygame.font.Font(font_path,22) if font_path else pygame.font.SysFont(None,24)
    font_s = pygame.font.Font(font_path,15) if font_path else pygame.font.SysFont(None,17)

    state = GameState()
    _grow_exits(state.dreams)

    d = state.dreams
    if d == 0:
        state.say("第一次來。你不知道從哪裡來的。",280)
    elif d < 4:
        state.say(f"你又回來了。這是第 {d} 次。",240)
    elif d < 10:
        state.say(random.choice([
            "你還在這裡。",f"第 {d} 次了。","也許你沒有離開過。",
        ]),220)
    else:
        state.say(random.choice(["……","你知道的。",f"{d}。"]),180)

    jw(f'(meet "{WORLD}" "{_now()}")')
    state.dreams = times_dreamed()

    mv_cd = 0
    run   = True

    while run:
        dt    = clock.tick(60)
        mv_cd = max(0, mv_cd-dt)
        state.tick()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: run = False

            if state.input_mode:
                if ev.type == pygame.TEXTINPUT:
                    if len(state.input_text) < 44:
                        state.input_text += ev.text
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_t):
                        state.input_mode = False; state.input_text = ''
                    elif ev.key == pygame.K_RETURN:
                        msg = state.input_text.strip()
                        if msg:
                            record_said(msg)
                            state.say("……這裡記住了。",200)
                            _grow_exits(state.dreams)
                        state.input_mode = False; state.input_text = ''
                    elif ev.key == pygame.K_BACKSPACE:
                        state.input_text = state.input_text[:-1]
                continue

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    run = False
                elif ev.key == pygame.K_t:
                    state.input_mode = True; state.input_text = ''
                    pygame.key.start_text_input()
                elif ev.key == pygame.K_e and not state.busy():
                    npc = near_npc(state)
                    obj = near_obj(state)
                    if npc:
                        state.say(get_dialogue(npc['id'], state))
                        note(f'talk:{npc["id"]}', 0.9)
                    elif obj:
                        handle_obj(obj['id'], state)

        if mv_cd==0 and not state.input_mode and not state.busy():
            keys = pygame.key.get_pressed()
            dx,dy = 0,0
            if keys[pygame.K_w] or keys[pygame.K_UP]:    dy=-1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy= 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx=-1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx= 1
            if dx or dy:
                nx,ny  = state.px+dx, state.py+dy
                exits  = state.room.get('exits',{})
                moved  = False
                if ny<0      and 'n' in exits: state.go(exits['n'],(COLS//2,ROWS-2)); moved=True
                elif ny>=ROWS and 's' in exits: state.go(exits['s'],(COLS//2,1));     moved=True
                elif nx>=COLS and 'e' in exits: state.go(exits['e'],(1,ROWS//2));     moved=True
                elif nx<0    and 'w' in exits: state.go(exits['w'],(COLS-2,ROWS//2)); moved=True
                if not moved and 0<=nx<COLS and 0<=ny<ROWS:
                    state.px,state.py = nx,ny
                mv_cd = 105

        draw_room(screen, state, font_s)
        draw_ui(screen, state, font, font_s)
        if state.input_mode: draw_input(screen, state, font, font_s)
        draw_fade(screen, state)
        pygame.display.flip()

    pygame.key.stop_text_input()
    pygame.quit()

if __name__ == '__main__':
    main()
