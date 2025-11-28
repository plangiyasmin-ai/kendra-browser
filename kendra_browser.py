import sys
import os
from PyQt5.QtCore import QUrl, Qt, QStandardPaths
from PyQt5.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QLineEdit, 
    QToolBar, 
    QAction, 
    QStatusBar,
    QProgressBar,
    QTabWidget, 
    QFileDialog, 
    QInputDialog,
    QStyle
)
from PyQt5.QtGui import QFont 
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineDownloadItem

# --- Konfigurasi Global ---
HOME_URL = QUrl("http://www.google.com")
BROWSER_NAME = "Kendra Browser"

# Menggunakan home directory user (~/) untuk folder 'downloads' agar lebih andal di Termux.
DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'downloads')

# Pastikan folder downloads ada
if not os.path.exists(DOWNLOAD_DIR):
    try:
        os.makedirs(DOWNLOAD_DIR)
    except Exception as e:
        # Fallback jika pembuatan direktori gagal
        DOWNLOAD_DIR = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        print(f"Gagal membuat folder ~/downloads: {e}. Menggunakan path default.")


class BrowserWindow(QMainWindow):
    """
    Kendra Browser - Aplikasi browser utama yang mendukung Tab, Download, dan Developer Tools.
    """
    
    def __init__(self):
        super().__init__()
        
        # Dapatkan style dari aplikasi untuk mengakses ikon standar
        self.style = QApplication.style() 
        
        # Menggunakan nama baru di judul
        self.setWindowTitle(f"{BROWSER_NAME} (Advanced)")
        self.setGeometry(100, 100, 1200, 800)
        
        # --- 1. QTabWidget sebagai wadah utama ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True) 
        self.tabs.setTabsClosable(True) 
        self.tabs.tabCloseRequested.connect(self.close_tab_or_window)
        self.setCentralWidget(self.tabs)
        
        self.showMaximized()
        self._create_navbar() 
        self._create_statusbar()

        self.tabs.currentChanged.connect(self.update_ui_on_tab_change)
        
        # --- 2. Inisialisasi Download Manager ---
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.handle_download_requested)
        
        # Tambahkan Tab pertama (Halaman Home)
        self._add_new_tab(HOME_URL, 'Home')

    # --- Implementasi Download Feature ---
    def handle_download_requested(self, download_item):
        """Menangani permintaan download dari browser."""
        # Menggunakan DOWNLOAD_DIR yang sudah dikonfigurasi
        default_path = os.path.join(DOWNLOAD_DIR, download_item.suggestedFileName())
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Simpan Berkas", 
            default_path,
            f"All Files (*);;{os.path.basename(download_item.suggestedFileName())} (*.*)"
        )

        if save_path:
            download_item.setPath(save_path)
            download_item.accept()
            self.status_bar.showMessage(f"Download dimulai: {download_item.suggestedFileName()}")
            
            download_item.finished.connect(lambda: self.download_finished(download_item))
        else:
            download_item.cancel()
            self.status_bar.showMessage("Download dibatalkan.")

    def download_finished(self, download_item):
        """Menampilkan pesan saat download selesai/gagal."""
        if download_item.state() == QWebEngineDownloadItem.DownloadInterrupted:
            self.status_bar.showMessage(f"Download gagal: {download_item.suggestedFileName()}")
        elif download_item.state() == QWebEngineDownloadItem.DownloadCompleted:
            self.status_bar.showMessage(f"Download selesai: {download_item.suggestedFileName()} disimpan di {download_item.path()}")

    # --- Tab and UI Management ---
    def _add_new_tab(self, qurl=None, label="Tab Baru"):
        """Membuat dan menambahkan tab baru dengan QWebEngineView."""
        if qurl is None:
            qurl = QUrl("about:blank") 

        browser = QWebEngineView()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda q: self.update_url_bar(q, browser))
        browser.loadProgress.connect(lambda p: self.update_progress(p, browser))
        browser.loadFinished.connect(lambda ok: self.update_title(browser))
        
        self.update_ui_on_tab_change(i)
        
    def close_tab_or_window(self, index):
        """Menutup tab yang diminta atau menutup jendela jika tab adalah yang terakhir."""
        if self.tabs.count() < 2:
            self.close()
        # Jika hanya ada satu tab, kita tidak menghapusnya agar jendela tetap terbuka (opsional, tapi lebih baik)
        elif self.tabs.count() > 0:
            self.tabs.removeTab(index)
        
    def update_ui_on_tab_change(self, index):
        """Memperbarui address bar dan judul saat tab diganti."""
        current_browser = self.tabs.currentWidget()
        if current_browser:
            self.update_url_bar(current_browser.url(), current_browser)
            self.update_title(current_browser)

    def _create_navbar(self):
        """Membuat dan mengatur Toolbar untuk navigasi dan fitur canggih."""
        navbar = QToolBar("Navigation")
        navbar.setMovable(False) 
        self.addToolBar(navbar)

        # Mengambil ikon standar dari QStyle
        style = self.style 

        # --- Tombol Navigasi ---
        back_btn = QAction(style.standardIcon(QStyle.SP_ArrowLeft), 'Kembali', self)
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        navbar.addAction(back_btn)

        forward_btn = QAction(style.standardIcon(QStyle.SP_ArrowRight), 'Maju', self)
        forward_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navbar.addAction(forward_btn)

        reload_btn = QAction(style.standardIcon(QStyle.SP_BrowserReload), 'Refresh', self)
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navbar.addAction(reload_btn)
        
        stop_btn = QAction(style.standardIcon(QStyle.SP_DialogCancelButton), 'Stop', self)
        stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        navbar.addAction(stop_btn)

        # Tombol Home menggunakan nama browser baru di tooltip
        home_btn = QAction(style.standardIcon(QStyle.SP_DesktopIcon), f'Home ({BROWSER_NAME})', self)
        home_btn.triggered.connect(lambda: self.tabs.currentWidget().setUrl(HOME_URL))
        navbar.addAction(home_btn)
        
        navbar.addSeparator()

        # --- Tombol Tab Management ---
        new_tab_btn = QAction(style.standardIcon(QStyle.SP_FileIcon), 'Tab Baru', self)
        new_tab_btn.triggered.connect(lambda: self._add_new_tab(HOME_URL, 'Tab Baru'))
        navbar.addAction(new_tab_btn)
        
        # Tombol Rename Tab (Simulasi Tab Grouping)
        rename_btn = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), 'Ganti Nama (Grup)', self)
        rename_btn.setToolTip("Gunakan ini untuk memberi nama grup tab, cth: [Kerja] Judul Tab")
        rename_btn.triggered.connect(self.rename_current_tab)
        navbar.addAction(rename_btn)
        
        navbar.addSeparator()
        
        # --- Tombol Inspect Element ---
        inspect_btn = QAction(style.standardIcon(QStyle.SP_DialogHelpButton), 'Inspect', self)
        inspect_btn.setToolTip("Buka Developer Tools (Inspect Element)")
        inspect_btn.triggered.connect(self.open_dev_tools)
        navbar.addAction(inspect_btn)


        # Input URL (address bar)
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)
        
        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False) 
        navbar.addWidget(self.progress_bar)
        
    def _create_statusbar(self):
        """Membuat status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Siap.")
    
    # --- Implementasi Inspect Element ---
    def open_dev_tools(self):
        """Membuka jendela Developer Tools (Inspect Element) pada tab aktif."""
        current_browser = self.tabs.currentWidget()
        if current_browser:
            # Trigger WebEngineAction.InspectElement untuk membuka DevTools
            current_browser.page().triggerAction(current_browser.page().WebEngineAction.InspectElement)

    # --- Implementasi Tab Grouping (Rename) ---
    def rename_current_tab(self):
        """Memungkinkan pengguna mengganti nama tab saat ini."""
        current_browser = self.tabs.currentWidget()
        if not current_browser:
            return

        current_text = self.tabs.tabText(self.tabs.currentIndex())
        
        new_text, ok = QInputDialog.getText(
            self, 
            'Ganti Nama Tab (Grup)', 
            'Masukkan nama baru (mis. [Kerja] Nama Laporan):', 
            QLineEdit.Normal, 
            current_text
        )

        if ok and new_text:
            self.tabs.setTabText(self.tabs.currentIndex(), new_text)

    # --- Utility Functions ---
    def navigate_to_url(self):
        """Memuat URL yang diketik di address bar pada tab yang sedang aktif."""
        current_browser = self.tabs.currentWidget()
        if not current_browser:
            return
            
        url = self.url_bar.text()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url
        
        current_browser.setUrl(QUrl(url))
        self.progress_bar.setVisible(True)

    def update_url_bar(self, q, browser):
        """Memperbarui teks di address bar hanya jika tab tersebut aktif."""
        if browser != self.tabs.currentWidget():
            return
            
        display_url = q.toString()
        self.url_bar.setText(display_url)
        self.url_bar.setCursorPosition(0)

    def update_title(self, browser):
        """Memperbarui judul tab dan judul jendela."""
        title = browser.page().title()
        index = self.tabs.indexOf(browser)
        
        # Hanya perbarui jika judul tab saat ini bukan nama grup buatan pengguna
        current_tab_text = self.tabs.tabText(index)
        if not current_tab_text.startswith('[') and title: 
             self.tabs.setTabText(index, title)
            
        if browser == self.tabs.currentWidget():
            self.setWindowTitle(f"{BROWSER_NAME} - {title}")

    def update_progress(self, progress, browser):
        """Memperbarui nilai progress bar hanya untuk tab yang aktif."""
        if browser != self.tabs.currentWidget():
            return

        self.progress_bar.setValue(progress)
        self.progress_bar.setVisible(progress > 0 and progress < 100)
        self.status_bar.showMessage(f"Memuat: {progress}%")
        
        if progress == 100:
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage("Selesai memuat.")


# --- 4. Memulai Aplikasi ---
if __name__ == '__main__':
    # Pengaturan DPI tinggi untuk tampilan yang lebih baik di layar mobile/tablet
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
    app = QApplication(sys.argv)
    window = BrowserWindow()
    sys.exit(app.exec_())
