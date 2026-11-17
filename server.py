from flask import Flask, request, jsonify
import sqlite3, json, os, re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlencode, urlsplit

BASE = Path(__file__).resolve().parent
DB_PATH = str(Path(os.environ.get("GIFTFINDER_DB", str(BASE / "giftly.db"))).expanduser().resolve())
STATIC_DIR = (BASE / "static").resolve()
if Path(DB_PATH).is_relative_to(STATIC_DIR):
    raise ValueError("GIFTFINDER_DB must be stored outside the public static directory")
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

SEED = [
 {"name":"Wireless Earbuds","price":1499,"emoji":"🎧","categories":["Technology","Music"],"occasions":["Birthday","Graduation","Friendship"],"why":"A useful everyday upgrade for someone who loves music, podcasts, or taking calls."},
 {"name":"Gaming Mouse","price":1299,"emoji":"🖱️","categories":["Technology","Gaming"],"occasions":["Birthday","Friendship","Farewell"],"why":"A practical gaming upgrade for someone who spends time playing PC games."},
 {"name":"Custom Photo Frame","price":699,"emoji":"🖼️","categories":["Art"],"occasions":["Birthday","Anniversary","Friendship"],"why":"A personal keepsake that turns a favourite memory into something they can display."},
 {"name":"Personalized Notebook","price":499,"emoji":"📓","categories":["Books","Art"],"occasions":["Birthday","Graduation","Farewell"],"why":"An affordable, thoughtful choice for students, planners, readers, and creative people."},
 {"name":"Fitness Smart Band","price":1899,"emoji":"⌚","categories":["Fitness","Technology","Sports"],"occasions":["Birthday","Graduation"],"why":"A handy companion for tracking everyday movement and fitness goals."},
 {"name":"Travel Organizer","price":899,"emoji":"🧳","categories":["Travel"],"occasions":["Birthday","Farewell","Graduation"],"why":"Keeps travel essentials tidy for someone who is happiest exploring somewhere new."},
 {"name":"Premium Coffee Mug","price":549,"emoji":"☕","categories":["Technology","Art"],"occasions":["Birthday","Friendship","Festival"],"why":"An everyday favourite that can feel personal with a design or message they love."},
 {"name":"Classic Novel Gift Set","price":999,"emoji":"📚","categories":["Books"],"occasions":["Birthday","Graduation","Farewell"],"why":"A cosy, meaningful pick for someone who always has another book on the go."},
 {"name":"Bluetooth Speaker","price":1799,"emoji":"🔊","categories":["Music","Technology"],"occasions":["Birthday","Friendship","Festival"],"why":"A fun fit for music lovers, from desk playlists to relaxed get-togethers."},
 {"name":"Sports Water Bottle","price":749,"emoji":"🏃","categories":["Sports","Fitness"],"occasions":["Birthday","Friendship"],"why":"A useful daily essential for someone with an active routine."},
 {"name":"Minimalist Backpack","price":1999,"emoji":"🎒","categories":["Fashion","Technology","Travel"],"occasions":["Graduation","Birthday","Farewell"],"why":"Combines everyday utility and a clean style for college, work, or weekend plans."},
 {"name":"Art Sketch Kit","price":1199,"emoji":"🎨","categories":["Art"],"occasions":["Birthday","Friendship","Graduation"],"why":"Encourages a creative hobby with tools they can use to make something of their own."},
 {"name":"Desk Plant Set","price":449,"emoji":"🪴","categories":["Art","Travel"],"occasions":["Birthday","Graduation","Friendship"],"why":"A cheerful low-maintenance touch of green for a desk or study corner."},
 {"name":"Instant Photo Printer","price":4299,"emoji":"📸","categories":["Technology","Art","Travel"],"occasions":["Birthday","Anniversary","Graduation"],"why":"Turns phone memories into tangible photos to share and display."},
 {"name":"Board Game Night Kit","price":1499,"emoji":"🎲","categories":["Gaming","Friendship"],"occasions":["Birthday","Friendship","Festival"],"why":"Creates a shared experience instead of another thing that sits on a shelf."},
 {"name":"Premium Sports Jersey","price":1599,"emoji":"🏏","categories":["Sports","Fashion"],"occasions":["Birthday","Graduation","Friendship"],"why":"A wearable pick for a fan who loves representing their favourite sport or team."},
 {"name":"Music Vinyl / Album Art","price":1299,"emoji":"🎶","categories":["Music","Art"],"occasions":["Birthday","Anniversary","Friendship"],"why":"A display-worthy keepsake for someone who connects memories to music."},
 {"name":"Travel Journal","price":599,"emoji":"🗺️","categories":["Travel","Books","Art"],"occasions":["Birthday","Farewell","Graduation"],"why":"A lovely place to collect trip notes, sketches, and little memories."},
 {"name":"Skincare Self-Care Box","price":1499,"emoji":"🧴","categories":["Fashion","Art"],"occasions":["Birthday","Anniversary","Festival"],"why":"A small ritual of relaxation for someone who enjoys a little self-care."},
 {"name":"Mechanical Keyboard","price":3499,"emoji":"⌨️","categories":["Technology","Gaming"],"occasions":["Birthday","Graduation","Farewell"],"why":"A tactile desk upgrade for a gamer, coder, or someone who loves their setup."},
 {"name":"Personalized Pendant","price":2499,"emoji":"💝","categories":["Fashion","Art"],"occasions":["Anniversary","Birthday"],"why":"A sentimental keepsake that can carry a name, date, or personal meaning."},
 {"name":"Mini Projector","price":4999,"emoji":"📽️","categories":["Technology","Gaming","Music"],"occasions":["Birthday","Graduation","Festival"],"why":"Makes movie nights and shared viewing feel like an event."},
 {"name":"Cricket Training Kit","price":1899,"emoji":"🏏","categories":["Sports","Fitness"],"occasions":["Birthday","Friendship","Graduation"],"why":"A useful training-themed gift for someone who lives and breathes cricket."},
 {"name":"Artisan Chocolate Box","price":799,"emoji":"🍫","categories":["Art"],"occasions":["Birthday","Anniversary","Festival","Friendship"],"why":"A sweet, easy-to-share treat that feels special without needing a big occasion."},
 {"name":"Premium Noise-Cancelling Headphones","price":8999,"emoji":"🎧","categories":["Technology","Music"],"occasions":["Birthday","Graduation","Anniversary"],"why":"A higher-end listening upgrade for someone who loves music, travel, or focused work."},
 {"name":"Weekend Stay Voucher","price":7499,"emoji":"🏨","categories":["Travel"],"occasions":["Anniversary","Birthday","Graduation"],"why":"A shared getaway can turn a milestone into a memory. Check dates and terms with the provider."}
]
BUDGETS={"0-500":(0,499),"500-1000":(500,999),"1000-2000":(1000,1999),"2000-5000":(2000,4999),"5000+":(5000,float("inf"))}

@contextmanager
def connect():
    c=sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    Path(DB_PATH).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS gifts(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE,price INTEGER,emoji TEXT,categories TEXT,occasions TEXT,why TEXT);
        CREATE TABLE IF NOT EXISTS wishlists(id INTEGER PRIMARY KEY AUTOINCREMENT,gift_id INTEGER REFERENCES gifts(id) ON DELETE CASCADE,created_at TEXT NOT NULL,owner_id TEXT NOT NULL DEFAULT 'legacy',UNIQUE(gift_id,owner_id));
        CREATE TABLE IF NOT EXISTS searches(id INTEGER PRIMARY KEY AUTOINCREMENT,brief TEXT NOT NULL,request_json TEXT NOT NULL,created_at TEXT NOT NULL,owner_id TEXT NOT NULL DEFAULT 'legacy');
        CREATE TABLE IF NOT EXISTS saved_links(id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,product_url TEXT NOT NULL,product_name TEXT NOT NULL,price INTEGER,retailer TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(owner_id,product_url));
        """)
        # Keep existing local databases usable while adding anonymous browser ownership.
        for table in ("wishlists", "searches"):
            columns={row[1] for row in c.execute(f"PRAGMA table_info({table})")}
            if "owner_id" not in columns:
                c.execute(f"ALTER TABLE {table} ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy'")
        # The original wishlist had UNIQUE(gift_id), which prevented two browsers
        # from saving the same catalog item. Rebuild it as an owner-scoped uniqueness rule.
        unique_gift=False
        for idx in c.execute("PRAGMA index_list(wishlists)").fetchall():
            if idx[2] and [r[2] for r in c.execute(f"PRAGMA index_info('{idx[1]}')").fetchall()]==["gift_id"]:
                unique_gift=True
        if unique_gift:
            c.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE wishlists_rebuilt(id INTEGER PRIMARY KEY AUTOINCREMENT,gift_id INTEGER REFERENCES gifts(id) ON DELETE CASCADE,created_at TEXT NOT NULL,owner_id TEXT NOT NULL DEFAULT 'legacy',UNIQUE(gift_id,owner_id));
            INSERT OR IGNORE INTO wishlists_rebuilt(id,gift_id,created_at,owner_id) SELECT id,gift_id,created_at,owner_id FROM wishlists;
            DROP TABLE wishlists;
            ALTER TABLE wishlists_rebuilt RENAME TO wishlists;
            COMMIT;
            """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_wishlists_owner ON wishlists(owner_id, id DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_searches_owner ON searches(owner_id, id DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_saved_links_owner ON saved_links(owner_id, id DESC)")
        c.executemany("INSERT OR IGNORE INTO gifts(name,price,emoji,categories,occasions,why) VALUES(?,?,?,?,?,?)",[(g["name"],g["price"],g["emoji"],json.dumps(g["categories"]),json.dumps(g["occasions"]),g["why"]) for g in SEED])

def row_gift(row):
    d=dict(row)
    d["categories"]=json.loads(d.pop("categories"))
    d["occasions"]=json.loads(d.pop("occasions"))
    return d

def public_gift(g):
    return {k:g[k] for k in ("id","name","price","emoji","categories","occasions","why","score","match_reasons","rank") if k in g}

def retailer_searches(interests,budget_hint=""):
    choices={
        "Fashion":["shoes","shirts","pants"],
        "Technology":["wireless headphones","smart watches","keyboards"],
        "Gaming":["gaming mice","game controllers","board games"],
        "Books":["novels","book gift sets","reading lights"],
        "Music":["headphones","bluetooth speakers","vinyl records"],
        "Sports":["sports jerseys","sports shoes","training gear"],
        "Art":["art kits","photo frames","sketchbooks"],
        "Fitness":["fitness bands","yoga mats","sports bottles"],
        "Travel":["travel bags","travel organizers","travel journals"]
    }
    terms=[]
    for category in interests:
        for term in choices.get(category,[]):
            if term not in terms:terms.append(term)
    if not terms:terms=["thoughtful gifts"]
    results=[]
    for term in terms[:3]:
        query=f"{term} gift {budget_hint}".strip()
        links=[{"retailer":"Amazon.in","url":"https://www.amazon.in/s?"+urlencode({"k":query})}]
        if "Fashion" in interests:
            slug=quote_plus(term.lower()).replace("+","-")
            links.append({"retailer":"Myntra","url":f"https://www.myntra.com/{slug}?rawQuery={quote_plus(query)}"})
        results.append({"query":query,"links":links})
    return results

def request_brief(r):
    name=r.get("recipientName") or ("my "+str(r.get("relationship") or "person").lower())
    return f"Gift for {name} · {r.get('age','age not set')} · {r.get('occasion','any occasion')} · {', '.join(r.get('interests') or []) or 'open to ideas'} · {r.get('budget','budget not set')}"

def owner_id():
    """Identify a browser-local profile; this is isolation, not authentication."""
    value=request.headers.get("X-Giftly-Client", "")
    if not re.fullmatch(r"[a-f0-9-]{36}", value):
        return None
    return value

def require_owner():
    value=owner_id()
    if not value:
        return None, (jsonify(error="A valid browser profile is required"), 400)
    return value, None

RELATIONSHIPS={"Best Friend","Friend","Partner","Sibling","Parent","Classmate"}
AGES={"Under 18","18–24","25–34","35–49","50+"}
OCCASIONS={"Birthday","Anniversary","Graduation","Festival","Farewell","Friendship"}
CATEGORIES={category for gift in SEED for category in gift["categories"]}

def valid_brief(r):
    if not isinstance(r, dict): return "Request body must be a JSON object"
    for key, allowed in (("relationship",RELATIONSHIPS),("age",AGES),("occasion",OCCASIONS)):
        if not isinstance(r.get(key),str) or r[key] not in allowed: return f"Invalid {key}"
    if not isinstance(r.get("interests"),list) or any(not isinstance(x,str) or x not in CATEGORIES for x in r["interests"]): return "interests must be a list of known categories"
    if len(r["interests"])>len(CATEGORIES): return "Too many interests"
    if len(set(r["interests"]))!=len(r["interests"]): return "interests cannot contain duplicates"
    name=r.get("recipientName","")
    if not isinstance(name,str) or len(name)>60: return "recipientName must be text up to 60 characters"
    budget=r.get("budget")
    if not isinstance(budget,str) or budget not in BUDGETS: return "Unknown budget range"
    return None

@app.get("/")
def home():
    return app.send_static_file("index.html")

@app.get("/api/health")
def health():
    with connect() as c:
        c.execute("SELECT 1")
        count=c.execute("SELECT COUNT(*) FROM gifts").fetchone()[0]
    return jsonify(status="ok",database="SQLite",catalog_count=count,timestamp=datetime.now(timezone.utc).isoformat())

@app.get("/api/gifts")
def gifts():
    with connect() as c: rows=c.execute("SELECT * FROM gifts ORDER BY name").fetchall()
    return jsonify(gifts=[row_gift(x) for x in rows])

@app.post("/api/recommend")
def recommend():
    r=request.get_json(silent=True) or {}
    error=valid_brief(r)
    if error:return jsonify(error=error),400
    client, failure=require_owner()
    if failure:return failure
    interests=r["interests"]
    low_price,max_price=BUDGETS[r["budget"]]
    with connect() as c: catalog=[row_gift(x) for x in c.execute("SELECT * FROM gifts").fetchall()]
    scored=[]
    for g in catalog:
        if not low_price<=g["price"]<=max_price: continue
        hits=[i for i in interests if i in g["categories"]]
        score=len(hits)*5+(4 if r["occasion"] in g["occasions"] else 0)
        reasons=[f"Matches {i}" for i in hits]
        if r["occasion"] in g["occasions"]:reasons.append(f"Fits {r['occasion']}")
        if r["relationship"]=="Partner" and r["occasion"]=="Anniversary" and "Anniversary" in g["occasions"]:score+=2;reasons.append("Keepsake-friendly")
        if r["relationship"]=="Classmate" and g["price"]<=1000:score+=2;reasons.append("Considerate classmate budget")
        if r.get("age")=="Under 18" and g["price"]<1000:score+=1;reasons.append("Under ₹1,000")
        g["score"]=score;g["match_reasons"]=reasons or ["Within your selected budget"];g["rank"]=0
        scored.append(g)
    scored.sort(key=lambda g:(-g["score"],g["price"],g["id"]))
    for i,g in enumerate(scored[:9],1):g["rank"]=i
    brief=request_brief(r); now=datetime.now(timezone.utc).isoformat()
    with connect() as c:
        cur=c.execute("INSERT INTO searches(brief,request_json,created_at,owner_id) VALUES(?,?,?,?)",(brief,json.dumps(r),now,client))
        search_id=cur.lastrowid
        c.execute("DELETE FROM searches WHERE owner_id=? AND id NOT IN (SELECT id FROM searches WHERE owner_id=? ORDER BY id DESC LIMIT 30)",(client,client))
    budget_hint=(f"under ₹{max_price:,}" if low_price==0 else f"₹{low_price:,} to under ₹{max_price+1:,}") if max_price!=float("inf") else "₹5,000+ budget"
    return jsonify(search_id=search_id,brief=brief,recommendations=[public_gift(g) for g in scored[:9]],retailer_searches=retailer_searches(interests,budget_hint))

@app.get("/api/wishlist")
def wishlist_get():
    client, failure=require_owner()
    if failure:return failure
    with connect() as c:
        rows=c.execute("SELECT g.* FROM wishlists w JOIN gifts g ON g.id=w.gift_id WHERE w.owner_id=? ORDER BY w.id DESC",(client,)).fetchall()
        links=c.execute("SELECT id,product_url,product_name,price,retailer,created_at FROM saved_links WHERE owner_id=? ORDER BY id DESC",(client,)).fetchall()
    items=[row_gift(x) for x in rows]
    items.extend({"id":f"link-{x['id']}","type":"link","name":x["product_name"],"price":x["price"],"retailer":x["retailer"],"product_url":x["product_url"],"created_at":x["created_at"]} for x in links)
    return jsonify(wishlist=items)

@app.post("/api/wishlist")
def wishlist_add():
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return jsonify(error="Request body must be a JSON object"),400
    gift_id=data.get("gift_id")
    if type(gift_id) is not int or gift_id<1:return jsonify(error="gift_id must be a positive integer"),400
    client, failure=require_owner()
    if failure:return failure
    with connect() as c:
        if not c.execute("SELECT 1 FROM gifts WHERE id=?",(gift_id,)).fetchone():return jsonify(error="Gift not found"),404
        c.execute("INSERT OR IGNORE INTO wishlists(gift_id,created_at,owner_id) VALUES(?,?,?)",(gift_id,datetime.now(timezone.utc).isoformat(),client))
        rows=c.execute("SELECT g.* FROM wishlists w JOIN gifts g ON g.id=w.gift_id WHERE w.owner_id=? ORDER BY w.id DESC",(client,)).fetchall()
    return jsonify(wishlist=[row_gift(x) for x in rows]),201

@app.delete("/api/wishlist/<int:gift_id>")
def wishlist_remove(gift_id):
    client, failure=require_owner()
    if failure:return failure
    with connect() as c:
        c.execute("DELETE FROM wishlists WHERE gift_id=? AND owner_id=?",(gift_id,client))
        rows=c.execute("SELECT g.* FROM wishlists w JOIN gifts g ON g.id=w.gift_id WHERE w.owner_id=? ORDER BY w.id DESC",(client,)).fetchall()
    return jsonify(wishlist=[row_gift(x) for x in rows])

@app.post("/api/wishlist/links")
def wishlist_save_link():
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return jsonify(error="Request body must be a JSON object"),400
    url=data.get("url")
    if not isinstance(url,str) or len(url)>2048:return jsonify(error="A product URL up to 2,048 characters is required"),400
    try:
        parsed=urlsplit(url.strip())
        port=parsed.port
    except ValueError:return jsonify(error="Invalid product URL"),400
    hosts={"amazon.in":"Amazon.in","www.amazon.in":"Amazon.in","myntra.com":"Myntra","www.myntra.com":"Myntra","flipkart.com":"Flipkart","www.flipkart.com":"Flipkart","ajio.com":"AJIO","www.ajio.com":"AJIO"}
    host=(parsed.hostname or "").lower()
    retailer=hosts.get(host)
    if parsed.scheme!="https" or not retailer or parsed.username or parsed.password or port not in (None,443):return jsonify(error="Use a direct HTTPS product link from Amazon.in, Myntra, Flipkart, or AJIO"),400
    name=data.get("name","")
    if not isinstance(name,str) or len(name)>160:return jsonify(error="Product name must be text up to 160 characters"),400
    name=name.strip() or f"Saved product from {retailer}"
    price=data.get("price")
    if price in (None,""):price=None
    elif type(price) is not int or not 0<=price<=10_000_000:return jsonify(error="Price must be a non-negative whole number"),400
    client,failure=require_owner()
    if failure:return failure
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO saved_links(owner_id,product_url,product_name,price,retailer,created_at) VALUES(?,?,?,?,?,?)",(client,url.strip(),name,price,retailer,datetime.now(timezone.utc).isoformat()))
    return jsonify(saved=True,retailer=retailer),201

@app.delete("/api/wishlist/links/<int:link_id>")
def wishlist_remove_link(link_id):
    client,failure=require_owner()
    if failure:return failure
    with connect() as c:c.execute("DELETE FROM saved_links WHERE id=? AND owner_id=?",(link_id,client))
    return jsonify(removed=True)

@app.get("/api/history")
def history():
    client, failure=require_owner()
    if failure:return failure
    with connect() as c: rows=c.execute("SELECT * FROM searches WHERE owner_id=? ORDER BY id DESC LIMIT 30",(client,)).fetchall()
    return jsonify(history=[{"id":r["id"],"brief":r["brief"],"request":json.loads(r["request_json"]),"created_at":r["created_at"]} for r in rows])

@app.delete("/api/history")
def history_clear():
    client, failure=require_owner()
    if failure:return failure
    with connect() as c: c.execute("DELETE FROM searches WHERE owner_id=?",(client,))
    return jsonify(history=[])

@app.post("/api/assistant")
def assistant():
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict): return jsonify(error="Request body must be a JSON object"),400
    message=data.get("message","")
    if not isinstance(message,str) or len(message)>500: return jsonify(error="message must be text up to 500 characters"),400
    message=message.strip()
    if not message:return jsonify(error="Please enter a message"),400
    client,failure=require_owner()
    if failure:return failure
    budget=None
    match=re.search(r"\b(?:under|below|less than|within|up\s+to|up\s+till|upto|not more than|max(?:imum)?)\b\s*(?:₹|rs\.?\s*)?([\d,]+)",message.lower())
    if match:
        try:budget=int(match.group(1).replace(",",""))
        except ValueError:pass
    interest_terms={"Technology":["technology","tech","coding","computer","gadget","phone"],"Gaming":["gaming","game","gamer","playstation","xbox"],"Books":["book","reading","novel","reader"],"Music":["music","song","headphone","concert"],"Sports":["sport","cricket","football","jersey"],"Fashion":["fashion","style","clothes","clothing","outfit","apparel","jewellery","shoe","sneaker","shirt","pant","trouser","jean","dress"],"Art":["art","drawing","creative","craft","photo"],"Fitness":["fitness","gym","workout","running"],"Travel":["travel","trip","explore","adventure"]}
    lower_message=message.lower()
    def mentions(term):
        return re.search(rf"\b{re.escape(term)}(?:s|es)?\b",lower_message) is not None
    interests=[cat for cat,terms in interest_terms.items() if any(mentions(t) for t in terms)]
    found_occasions=[o for o in ["Birthday","Anniversary","Graduation","Farewell","Festival"] if re.search(rf"\b{re.escape(o.lower())}\b",lower_message)]
    occasion=min(found_occasions,key=lambda o:lower_message.find(o.lower()),default=None)
    with connect() as c: catalog=[row_gift(x) for x in c.execute("SELECT * FROM gifts").fetchall()]
    scored=[]
    for g in catalog:
        if budget is not None and g["price"]>budget:continue
        score=sum(5 for i in interests if i in g["categories"])
        if occasion and occasion in g["occasions"]:score+=3
        reasons=[f"Matches {i}" for i in interests if i in g["categories"]]
        if occasion and occasion in g["occasions"]:reasons.append(f"Fits {occasion}")
        g["score"]=score;g["match_reasons"]=reasons or ([f"Under ₹{budget:,}"] if budget is not None else ["A versatile catalog pick"]);g["rank"]=0;scored.append(g)
    scored.sort(key=lambda g:(-g["score"],g["price"],g["id"]))
    for i,g in enumerate(scored[:3],1):g["rank"]=i
    if interests:
        idea="I picked up on "+", ".join(interests)+". "
    else:idea="I’ll start with versatile, thoughtful options. "
    if budget is not None:idea+=f"I kept the shortlist at ₹{budget:,} or less. "
    names=", ".join(g["name"] for g in scored[:3]) or "a personalized notebook or a small experience"
    reply=idea+f"A few ideas to explore: {names}. Think about whether they prefer something useful, sentimental, or an experience you can share. Want to narrow it down further?"
    links=retailer_searches(interests,f"under ₹{budget:,}" if budget is not None else "")
    now=datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("INSERT INTO searches(brief,request_json,created_at,owner_id) VALUES(?,?,?,?)",(message,json.dumps({"type":"assistant","message":message}),now,client))
        c.execute("DELETE FROM searches WHERE owner_id=? AND id NOT IN (SELECT id FROM searches WHERE owner_id=? ORDER BY id DESC LIMIT 30)",(client,client))
    return jsonify(reply=reply,recommendations=[public_gift(g) for g in scored[:3]],retailer_searches=links)

@app.get("/api/stats")
def stats():
    client, failure=require_owner()
    if failure:return failure
    with connect() as c:
        gifts_count=c.execute("SELECT COUNT(*) FROM gifts").fetchone()[0]
        wish_count=c.execute("SELECT (SELECT COUNT(*) FROM wishlists WHERE owner_id=?)+(SELECT COUNT(*) FROM saved_links WHERE owner_id=?)",(client,client)).fetchone()[0]
        search_count=c.execute("SELECT COUNT(*) FROM searches WHERE owner_id=?",(client,)).fetchone()[0]
    return jsonify(catalog=gifts_count,wishlist=wish_count,searches=search_count)

@app.errorhandler(500)
def server_error(_):
    app.logger.exception("Unhandled server error")
    return jsonify(error="Something went wrong on the server. Check the terminal for details."),500

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Request body is too large"),413

@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response

init_db()
if __name__=="__main__":
    print("Giftly backend starting at http://127.0.0.1:5000")
    print(f"SQLite database: {DB_PATH}")
    app.run(host=os.environ.get("HOST","127.0.0.1"),port=int(os.environ.get("PORT","5000")),debug=os.environ.get("GIFTFINDER_DEBUG","0")=="1")

