import sys
import os
import requests 
import webbrowser 
from pathlib import Path 
import qdarkstyle 
import pandas as pd
import numpy as np 

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QFileDialog, QSpinBox, QHeaderView, QMessageBox,
    QGroupBox, QStyle 
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPalette

API_URL = "http://127.0.0.1:8000/puanla-toplu/"

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

class Worker(QThread):
    finished = pyqtSignal(dict) 
    error = pyqtSignal(str) 
    def __init__(self, ilan_yolu, cv_yollari, esik_puani):
        super().__init__()
        self.ilan_yolu, self.cv_yollari, self.esik_puani = ilan_yolu, cv_yollari, esik_puani
    def run(self):
        try:
            files = [('is_ilani', (os.path.basename(self.ilan_yolu), open(self.ilan_yolu, 'rb'), 'application/octet-stream'))]
            for cv in self.cv_yollari: files.append(('cv_listesi', (os.path.basename(cv), open(cv, 'rb'), 'application/octet-stream')))
            res = requests.post(API_URL, files=files, data={'esik_puani': self.esik_puani})
            if res.status_code == 200: self.finished.emit(res.json())
            else: self.error.emit(f"Hata: {res.status_code}")
        except Exception as e: self.error.emit(str(e))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Analiz")
        self.setGeometry(100, 100, 1200, 750)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(10,10,10,10)

        gbox_top = QGroupBox("Dosya Seçimi ve Ayarlar")
        top_layout = QHBoxLayout()
        
        self.btn_ilan_sec = QPushButton("İlan Seç"); self.btn_ilan_sec.clicked.connect(self.ilan_dosyasi_sec)
        self.btn_cv_sec = QPushButton("CV'leri Seç"); self.btn_cv_sec.clicked.connect(self.cv_dosyalari_sec)
        
        self.spin_esik_puani = QSpinBox()
        self.spin_esik_puani.setValue(50)
        self.spin_esik_puani.setFixedWidth(60)
        
        self.btn_baslat = QPushButton("BAŞLAT"); self.btn_baslat.clicked.connect(self.taramayi_baslat)
        self.btn_baslat.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        
        top_layout.addWidget(self.btn_ilan_sec)
        top_layout.addWidget(self.btn_cv_sec)
        top_layout.addSpacing(20) 
        top_layout.addWidget(QLabel("Eşik:"))
        top_layout.addWidget(self.spin_esik_puani)
        top_layout.addStretch() 
        top_layout.addWidget(self.btn_baslat)
        
        gbox_top.setLayout(top_layout)
        self.layout.addWidget(gbox_top)

        gbox_sonuclar = QGroupBox("Analiz Paneli")
        h_layout_ana = QHBoxLayout()

        v_layout_sol = QVBoxLayout()
        self.tablo_sonuclar = QTableWidget()
        self.tablo_sonuclar.setColumnCount(4) 
        self.tablo_sonuclar.setHorizontalHeaderLabels(["Dosya", "Aday İsmi", "Email", "Puan"])
        self.tablo_sonuclar.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tablo_sonuclar.setColumnWidth(0, 180) 
        self.tablo_sonuclar.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tablo_sonuclar.setColumnWidth(1, 150) 
        self.tablo_sonuclar.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tablo_sonuclar.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tablo_sonuclar.setColumnWidth(3, 80)
        
        self.tablo_sonuclar.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        v_layout_sol.addWidget(self.tablo_sonuclar)
        
        self.btn_excel = QPushButton("Excel'e Aktar")
        self.btn_excel.clicked.connect(self.excele_kaydet)
        v_layout_sol.addWidget(self.btn_excel)
        h_layout_ana.addLayout(v_layout_sol, 2) 

        v_layout_sag = QVBoxLayout()
        self.lbl_grafik_baslik = QLabel("Genel Puan Dağılımı")
        self.lbl_grafik_baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_grafik_baslik.setStyleSheet("font-weight: bold; font-size: 14px; color: cyan;")
        v_layout_sag.addWidget(self.lbl_grafik_baslik)
        
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        v_layout_sag.addWidget(self.canvas)
        
        self.lbl_ipucu = QLabel("Yetenek Radarını görmek için listeden bir kişiye tıklayın.")
        self.lbl_ipucu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ipucu.setStyleSheet("font-style: italic; color: gray;")
        v_layout_sag.addWidget(self.lbl_ipucu)

        h_layout_ana.addLayout(v_layout_sag, 1) 
        gbox_sonuclar.setLayout(h_layout_ana)
        self.layout.addWidget(gbox_sonuclar, 1)

        self.lbl_durum = QLabel("Hazır.")
        self.layout.addWidget(self.lbl_durum)

        self.tablo_sonuclar.cellClicked.connect(self.tablo_tiklandi_yoneticisi)
        
        self.is_ilani_yolu = ""
        self.cv_yollari = []
        self.worker = None
        self.son_sonuclar = []

    def tablo_tiklandi_yoneticisi(self, row, column):
        item_isim = self.tablo_sonuclar.item(row, 1)
        if item_isim:
            isim = item_isim.text()
            yetenekler = item_isim.data(Qt.ItemDataRole.UserRole)
            if yetenekler:
                self.ciz_radar_grafigi(isim, yetenekler)
            else:
                self.resete_don()

        if column == 0:
            item_dosya = self.tablo_sonuclar.item(row, 0)
            path = item_dosya.data(Qt.ItemDataRole.UserRole)
            if path:
                try:
                    webbrowser.open(Path(path).as_uri())
                    self.lbl_durum.setText(f"Dosya açılıyor: {item_dosya.text()}")
                except Exception as e:
                    self.lbl_durum.setText(f"Hata: {e}")

    def ilan_dosyasi_sec(self):
        path, _ = QFileDialog.getOpenFileName(self, "İlan Seç")
        if path: self.is_ilani_yolu = path; self.lbl_durum.setText(f"İlan: {os.path.basename(path)}")

    def cv_dosyalari_sec(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "CV Seç")
        if paths: self.cv_yollari = paths; self.lbl_durum.setText(f"{len(paths)} CV seçildi")

    def taramayi_baslat(self):
        if not self.is_ilani_yolu or not self.cv_yollari: return
        self.btn_baslat.setEnabled(False)
        self.lbl_durum.setText("Analiz ediliyor...")
        self.canvas.figure.clear()
        self.canvas.draw()
        self.worker = Worker(self.is_ilani_yolu, self.cv_yollari, self.spin_esik_puani.value())
        self.worker.finished.connect(self.tarama_bitti)
        self.worker.error.connect(lambda e: self.lbl_durum.setText(f"Hata: {e}"))
        self.worker.start()

    def tarama_bitti(self, data):
        self.btn_baslat.setEnabled(True)
        self.son_sonuclar = data.get("sonuclar", [])
        self.lbl_durum.setText(f"Tamamlandı. {len(self.son_sonuclar)} sonuç.")
        path_map = {os.path.basename(p): p for p in self.cv_yollari}
        self.tablo_sonuclar.setRowCount(len(self.son_sonuclar))
        
        link_font = QFont(); link_font.setUnderline(True)
        link_color = QBrush(self.palette().color(QPalette.ColorRole.Link))
        puanlar = []
        
        for i, s in enumerate(self.son_sonuclar):
            puanlar.append(s['puan'])
            cv_adi = s['cv_adi']
            item_dosya = QTableWidgetItem(cv_adi)
            full_path = path_map.get(cv_adi)
            if full_path:
                item_dosya.setFont(link_font)
                item_dosya.setForeground(link_color)
                item_dosya.setData(Qt.ItemDataRole.UserRole, full_path)
            item_isim = QTableWidgetItem(s['isim'])
            item_isim.setData(Qt.ItemDataRole.UserRole, s.get('yetenekler', {}))
            self.tablo_sonuclar.setItem(i, 0, item_dosya)
            self.tablo_sonuclar.setItem(i, 1, item_isim)
            self.tablo_sonuclar.setItem(i, 2, QTableWidgetItem(s['email']))
            self.tablo_sonuclar.setItem(i, 3, QTableWidgetItem(str(s['puan'])))
        self.ciz_pasta_grafigi(puanlar)

    def resete_don(self):
        puanlar = [float(self.tablo_sonuclar.item(r, 3).text()) for r in range(self.tablo_sonuclar.rowCount())]
        self.ciz_pasta_grafigi(puanlar)

    def ciz_pasta_grafigi(self, puanlar):
        self.lbl_grafik_baslik.setText("Genel Puan Dağılımı")
        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111)
        yuksek = len([p for p in puanlar if p >= 80])
        orta = len([p for p in puanlar if 60 <= p < 80])
        dusuk = len([p for p in puanlar if p < 60])
        if puanlar:
            ax.pie([yuksek, orta, dusuk], labels=["Yüksek", "Orta", "Düşük"], 
                   colors=['#4CAF50', '#FFC107', '#F44336'], autopct='%1.1f%%', 
                   textprops={'color':"white"})
        
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def ciz_radar_grafigi(self, isim, yetenekler):
        self.lbl_grafik_baslik.setText(f"{isim} - Yetenek Radarı")
        kategoriler = list(yetenekler.keys())
        degerler = list(yetenekler.values())

        degerler += degerler[:1]
        angles = np.linspace(0, 2 * np.pi, len(kategoriler), endpoint=False).tolist()
        angles += angles[:1]

        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111, polar=True)
        
        ax.plot(angles, degerler, color='#00FFFF', linewidth=2, linestyle='solid')
        ax.fill(angles, degerler, color='#00FFFF', alpha=0.25)
        
        ax.set_xticks(angles[:-1])
        
        ax.tick_params(axis='x', colors='white', pad=10)
        ax.set_xticklabels(kategoriler, color='white', size=9)
        
        ax.set_rlabel_position(0)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(["1", "2", "3", "4", "5"], color="gray", size=7)
        ax.set_ylim(0, 5)
        ax.set_facecolor('#2b2b2b')
        ax.spines['polar'].set_color('gray')
        ax.grid(color='gray', linestyle='--', alpha=0.5)
        
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def excele_kaydet(self):
        if not self.son_sonuclar: return
        path, _ = QFileDialog.getSaveFileName(self, "Kaydet", "rapor.xlsx", "Excel (*.xlsx)")
        if path:
            pd.DataFrame(self.son_sonuclar).to_excel(path, index=False)
            QMessageBox.information(self, "Bilgi", "Kaydedildi.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())