from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
import fitz
import docx
import shutil
import aiofiles
from typing import List
import re 

app = FastAPI(title="CV Puanlama API")

YETENEK_KATEGORILERI = {
    "Backend": [
        "python", "java", "c#", ".net", "php", "go", "golang", "ruby", "nodejs", "node.js", "express",
        "django", "flask", "fastapi", "spring", "spring boot", "laravel", "asp.net", "rest", "graphql",
        "microservices", "soap", "redis", "rabbitmq", "kafka", "algorithm", "oop", "design patterns",
        "solid", "mvc", "entity framework", "hibernate"
    ],
    "Frontend": [
        "html", "html5", "css", "css3", "javascript", "js", "typescript", "ts", "react", "react.js",
        "angular", "vue", "vue.js", "next.js", "nuxt.js", "jquery", "bootstrap", "tailwind", "sass",
        "less", "redux", "webpack", "babel", "responsive", "ui/ux", "figma", "adobe xd", "material ui",
        "ajax", "json", "dom"
    ],
    "Veri & AI": [
        "sql", "mysql", "postgresql", "mongodb", "nosql", "sqlite", "oracle", "t-sql", "pl/sql",
        "python", "pandas", "numpy", "scikit-learn", "matplotlib", "seaborn", "tensorflow", "pytorch",
        "keras", "opencv", "nlp", "llm", "generative ai", "data science", "big data", "hadoop", "spark",
        "power bi", "tableau", "excel", "data analysis", "etl", "yolo", "hugging face"
    ],
    "DevOps & Cloud": [
        "git", "github", "gitlab", "bitbucket", "docker", "kubernetes", "k8s", "jenkins", "ci/cd",
        "aws", "amazon web services", "azure", "google cloud", "gcp", "terraform", "ansible", "linux",
        "bash", "shell", "nginx", "apache", "ubuntu", "centos", "prometheus", "grafana", "jira", 
        "agile", "scrum", "heroku", "digitalocean"
    ],
    "Mobil": [
        "flutter", "dart", "react native", "swift", "ios", "kotlin", "android", "java", "xamarin",
        "ionic", "objective-c", "mobile app", "firebase", "app store", "play store", "swiftui", "jetpack compose"
    ],
    "Sistem & Güvenlik": [
        "c", "c++", "cpp", "assembly", "embedded", "arduino", "raspberry pi", "stm32", "iot",
        "network", "tcp/ip", "http", "https", "dns", "cyber security", "siber güvenlik", "penetration testing",
        "owasp", "cryptography", "firewall", "wireshark", "kali linux", "ethical hacking", "metasploit",
        "işletim sistemleri", "mikroişlemci"
    ]
}

try:
    print("AI Modeli yükleniyor...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("AI Modeli başarıyla yüklendi.")
except:
    model = None

def metin_cikar(dosya_yolu):
    uzanti = os.path.splitext(dosya_yolu)[1].lower()
    metin = ""
    try:
        if uzanti == ".txt":
            with open(dosya_yolu, 'r', encoding='utf-8') as f: metin = f.read()
        elif uzanti == ".pdf":
            with fitz.open(dosya_yolu) as doc:
                for page in doc: metin += page.get_text()
        elif uzanti == ".docx":
            doc = docx.Document(dosya_yolu)
            for paragraph in doc.paragraphs: metin += paragraph.text + "\n"
    except: return None
    return metin

def bilgileri_ayikla(metin):
    bilgiler = {"isim": "Bulunamadı", "email": "Bulunamadı"}
    if not metin: return bilgiler
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', metin)
    if email_match: bilgiler["email"] = email_match.group(0)

    satirlar = [s.strip() for s in metin.split('\n') if s.strip()]
    if satirlar:
        olasi = satirlar[0]
        if len(olasi.split()) < 5 and "@" not in olasi: bilgiler["isim"] = olasi
        elif len(satirlar) > 1: bilgiler["isim"] = satirlar[1]
    return bilgiler

def yetenek_skoru_hesapla(cv_metni):
    """CV'deki kelimeleri kategorilere göre sayar ve skor üretir."""
    cv_lower = cv_metni.lower()
    skorlar = {}
    
    for kategori, kelimeler in YETENEK_KATEGORILERI.items():
        bulunan = 0
        for kelime in kelimeler:
            if kelime == "c" or kelime == "go": 
                if f" {kelime} " in cv_lower or f"{kelime}," in cv_lower:
                    bulunan += 1
            elif kelime in cv_lower:
                bulunan += 1
        raw_score = min(bulunan, 5) 
        skorlar[kategori] = raw_score
        
    return skorlar

def uyum_skoru_hesapla(ilan, cv, model):
    if not ilan or not cv: return 0.0
    return float(cosine_similarity(model.encode([ilan]), model.encode([cv]))[0][0])

@app.post("/puanla-toplu/")
async def puanla_toplu_cvler(
    is_ilani: UploadFile = File(...),
    cv_listesi: List[UploadFile] = File(...),
    esik_puani: int = Form(default=70)
):
    if model is None: raise HTTPException(500, "Model yok")
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    ilan_path = os.path.join(temp_dir, is_ilani.filename)
    
    try:
        async with aiofiles.open(ilan_path, 'wb') as out_file:
            content = await is_ilani.read()
            await out_file.write(content)
        ilan_metni = metin_cikar(ilan_path)

        sonuclar = []
        for cv in cv_listesi:
            cv_path = os.path.join(temp_dir, cv.filename)
            async with aiofiles.open(cv_path, 'wb') as out_file:
                content = await cv.read()
                await out_file.write(content)
            cv_metni = metin_cikar(cv_path)
            
            if cv_metni:
                skor = uyum_skoru_hesapla(ilan_metni, cv_metni, model)
                puan = round(skor * 100, 2)
                
                if puan >= esik_puani:
                    kisisel = bilgileri_ayikla(cv_metni)
                    yetenek_skorlari = yetenek_skoru_hesapla(cv_metni)
                    
                    sonuclar.append({
                        "cv_adi": cv.filename,
                        "isim": kisisel["isim"],
                        "email": kisisel["email"],
                        "puan": puan,
                        "yetenekler": yetenek_skorlari
                    })
            os.remove(cv_path)

        sonuclar.sort(key=lambda x: x['puan'], reverse=True)
        return {"sonuclar": sonuclar, "basarili_cv_sayisi": len(sonuclar)}
    except Exception as e: raise HTTPException(500, str(e))
    finally:
        if os.path.exists(ilan_path): os.remove(ilan_path)