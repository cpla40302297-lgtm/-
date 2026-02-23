"""
N Band Writer - 네이버 밴드 자동 게시물 작성 프로그램
메인 GUI 애플리케이션
"""
import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
from typing import Optional, List

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.band_api import BandAPI, BandAPIError
from src.config_manager import ConfigManager
from src.scheduler import Scheduler, ScheduledPost


# ─── 컬러 팔레트 ─────────────────────────────────────────────
C_PRIMARY   = "#03c75a"   # 밴드 그린
C_PRIMARY_D = "#02a34e"   # 짙은 그린
C_BG        = "#f5f6fa"   # 배경
C_WHITE     = "#ffffff"
C_SIDEBAR   = "#1a1a2e"   # 사이드바 다크
C_SIDEBAR_H = "#16213e"   # 사이드바 호버
C_TEXT      = "#2c3e50"
C_TEXT_L    = "#7f8c8d"
C_BORDER    = "#e0e0e0"
C_ERROR     = "#e74c3c"
C_WARNING   = "#f39c12"
C_SUCCESS   = "#27ae60"


class NBandWriterApp(tk.Tk):
    """메인 애플리케이션"""
    
    def __init__(self):
        super().__init__()
        
        self.title("N Band Writer - 네이버 밴드 자동 게시물")
        self.geometry("1000x720")
        self.minsize(900, 650)
        self.configure(bg=C_BG)
        
        # 아이콘 설정 (없으면 무시)
        try:
            self.iconbitmap(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
        except:
            pass
        
        # 모듈 초기화
        self.config_mgr = ConfigManager()
        self.api = BandAPI(
            client_id=self.config_mgr.get("client_id", ""),
            client_secret=self.config_mgr.get("client_secret", ""),
        )
        
        # 저장된 토큰 복원
        saved_token = self.config_mgr.get("access_token", "")
        if saved_token:
            self.api.set_access_token(saved_token)
        
        # 스케줄러
        self.scheduler = Scheduler()
        self.scheduler.set_post_callback(self._execute_scheduled_post)
        self.scheduler.set_update_callback(self._refresh_schedule_ui)
        self.scheduler.start()
        
        # 상태 변수
        self.bands: list = []
        self.selected_band: Optional[dict] = None
        self.attached_images: List[str] = []
        self._current_page = "write"
        
        # 스타일 설정
        self._setup_styles()
        
        # UI 구성
        self._build_ui()
        
        # 인증 상태 확인
        self.after(500, self._check_auth_on_startup)
    
    def _setup_styles(self):
        """ttk 스타일 설정"""
        style = ttk.Style(self)
        style.theme_use("clam")
        
        style.configure("TFrame", background=C_BG)
        style.configure("White.TFrame", background=C_WHITE)
        
        style.configure(
            "Primary.TButton",
            background=C_PRIMARY,
            foreground=C_WHITE,
            font=("맑은 고딕", 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(16, 8),
        )
        style.map("Primary.TButton",
            background=[("active", C_PRIMARY_D), ("disabled", "#aaaaaa")],
            foreground=[("disabled", "#eeeeee")],
        )
        
        style.configure(
            "Secondary.TButton",
            background=C_WHITE,
            foreground=C_TEXT,
            font=("맑은 고딕", 10),
            borderwidth=1,
            relief="solid",
            padding=(12, 7),
        )
        style.map("Secondary.TButton",
            background=[("active", "#f0f0f0")],
        )
        
        style.configure(
            "Danger.TButton",
            background=C_ERROR,
            foreground=C_WHITE,
            font=("맑은 고딕", 9),
            borderwidth=0,
            padding=(10, 6),
        )
        style.map("Danger.TButton", background=[("active", "#c0392b")])
        
        style.configure("TLabel", background=C_BG, foreground=C_TEXT, font=("맑은 고딕", 10))
        style.configure("Title.TLabel", font=("맑은 고딕", 13, "bold"), foreground=C_TEXT)
        style.configure("Sub.TLabel", font=("맑은 고딕", 9), foreground=C_TEXT_L)
        style.configure("White.TLabel", background=C_WHITE)
        
        style.configure("TCombobox", font=("맑은 고딕", 10))
        style.configure("TEntry", font=("맑은 고딕", 10))
        style.configure("TCheckbutton", background=C_BG, font=("맑은 고딕", 10))
        
        style.configure(
            "Treeview",
            background=C_WHITE,
            fieldbackground=C_WHITE,
            foreground=C_TEXT,
            rowheight=32,
            font=("맑은 고딕", 9),
        )
        style.configure("Treeview.Heading", font=("맑은 고딕", 9, "bold"))
        style.map("Treeview", background=[("selected", C_PRIMARY)])
    
    # ─── UI 빌드 ─────────────────────────────────────────────
    def _build_ui(self):
        """전체 레이아웃 구성"""
        # 사이드바
        self.sidebar = tk.Frame(self, bg=C_SIDEBAR, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # 메인 영역
        self.main_frame = tk.Frame(self, bg=C_BG)
        self.main_frame.pack(side="left", fill="both", expand=True)
        
        self._build_sidebar()
        self._build_main_area()
    
    def _build_sidebar(self):
        """사이드바 구성"""
        # 로고
        logo_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR, pady=20)
        logo_frame.pack(fill="x")
        
        tk.Label(
            logo_frame, text="🎵 N Band Writer",
            bg=C_SIDEBAR, fg=C_PRIMARY,
            font=("맑은 고딕", 13, "bold"), pady=10
        ).pack()
        
        tk.Label(
            logo_frame, text="네이버 밴드 자동화 도구",
            bg=C_SIDEBAR, fg="#8888aa",
            font=("맑은 고딕", 8)
        ).pack()
        
        # 구분선
        tk.Frame(self.sidebar, bg="#2a2a4a", height=1).pack(fill="x", padx=15, pady=8)
        
        # 네비게이션 버튼
        nav_items = [
            ("✏️  게시물 작성", "write"),
            ("📅  예약 게시", "schedule"),
            ("📋  템플릿 관리", "template"),
            ("⚙️  설정", "settings"),
        ]
        
        self.nav_buttons = {}
        for label, page_id in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=label,
                bg=C_SIDEBAR,
                fg="#c0c0d8",
                font=("맑은 고딕", 10),
                activebackground=C_SIDEBAR_H,
                activeforeground=C_WHITE,
                relief="flat",
                anchor="w",
                padx=20,
                pady=10,
                cursor="hand2",
                command=lambda p=page_id: self._switch_page(p),
            )
            btn.pack(fill="x")
            self.nav_buttons[page_id] = btn
        
        # 하단 인증 상태
        self.auth_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        self.auth_frame.pack(side="bottom", fill="x", pady=15, padx=15)
        
        self.auth_status_label = tk.Label(
            self.auth_frame, text="● 미인증",
            bg=C_SIDEBAR, fg=C_ERROR,
            font=("맑은 고딕", 9)
        )
        self.auth_status_label.pack(anchor="w")
        
        self.user_name_label = tk.Label(
            self.auth_frame, text="",
            bg=C_SIDEBAR, fg="#8888aa",
            font=("맑은 고딕", 8)
        )
        self.user_name_label.pack(anchor="w")
    
    def _build_main_area(self):
        """메인 컨텐츠 영역"""
        # 헤더
        self.header = tk.Frame(self.main_frame, bg=C_WHITE, height=56)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        
        self.page_title = tk.Label(
            self.header, text="게시물 작성",
            bg=C_WHITE, fg=C_TEXT,
            font=("맑은 고딕", 14, "bold"),
            padx=20
        )
        self.page_title.pack(side="left", fill="y")
        
        tk.Frame(self.main_frame, bg=C_BORDER, height=1).pack(fill="x")
        
        # 페이지 컨테이너
        self.page_container = tk.Frame(self.main_frame, bg=C_BG)
        self.page_container.pack(fill="both", expand=True)
        
        # 각 페이지 생성
        self.pages = {}
        self.pages["write"] = self._build_write_page()
        self.pages["schedule"] = self._build_schedule_page()
        self.pages["template"] = self._build_template_page()
        self.pages["settings"] = self._build_settings_page()
        
        # 초기 페이지
        self._switch_page("write")
    
    # ─── 게시물 작성 페이지 ──────────────────────────────────
    def _build_write_page(self) -> tk.Frame:
        frame = tk.Frame(self.page_container, bg=C_BG)
        
        # 좌우 2열 레이아웃
        left = tk.Frame(frame, bg=C_BG)
        left.pack(side="left", fill="both", expand=True, padx=(15, 8), pady=15)
        
        right = tk.Frame(frame, bg=C_BG, width=260)
        right.pack(side="right", fill="y", padx=(0, 15), pady=15)
        right.pack_propagate(False)
        
        # ── 왼쪽: 게시물 작성 영역 ──
        card1 = self._make_card(left, "밴드 선택")
        
        band_row = tk.Frame(card1, bg=C_WHITE)
        band_row.pack(fill="x", pady=(0, 5))
        
        self.band_var = tk.StringVar(value="밴드를 선택하세요")
        self.band_combo = ttk.Combobox(
            band_row, textvariable=self.band_var,
            state="readonly", font=("맑은 고딕", 10), width=30
        )
        self.band_combo.pack(side="left", fill="x", expand=True)
        self.band_combo.bind("<<ComboboxSelected>>", self._on_band_select)
        
        ttk.Button(
            band_row, text="🔄 새로고침",
            style="Secondary.TButton",
            command=self._refresh_bands
        ).pack(side="left", padx=(6, 0))
        
        # 본문 작성
        card2 = self._make_card(left, "게시물 내용")
        
        self.content_text = scrolledtext.ScrolledText(
            card2,
            font=("맑은 고딕", 11),
            wrap="word",
            height=12,
            relief="flat",
            bg="#fafafa",
            fg=C_TEXT,
            insertbackground=C_PRIMARY,
            padx=8, pady=8,
            undo=True,
        )
        self.content_text.pack(fill="both", expand=True)
        
        # 글자 수 카운터
        self.char_count_label = tk.Label(
            card2, text="0자",
            bg=C_WHITE, fg=C_TEXT_L,
            font=("맑은 고딕", 8), anchor="e"
        )
        self.char_count_label.pack(fill="x", pady=(3, 0))
        self.content_text.bind("<KeyRelease>", self._update_char_count)
        
        # 이미지 첨부
        card3 = self._make_card(left, "이미지 첨부 (선택)")
        
        img_btn_row = tk.Frame(card3, bg=C_WHITE)
        img_btn_row.pack(fill="x", pady=(0, 6))
        
        ttk.Button(
            img_btn_row, text="📷 이미지 추가",
            style="Secondary.TButton",
            command=self._add_image
        ).pack(side="left")
        
        ttk.Button(
            img_btn_row, text="🗑️ 전체 삭제",
            style="Danger.TButton",
            command=self._clear_images
        ).pack(side="left", padx=(6, 0))
        
        self.img_listbox = tk.Listbox(
            card3, height=3,
            font=("맑은 고딕", 9),
            bg="#fafafa", relief="flat",
            selectmode="single",
        )
        self.img_listbox.pack(fill="x")
        
        # ── 오른쪽: 옵션 / 작성 버튼 ──
        card_opt = self._make_card(right, "게시 옵션")
        
        self.push_var = tk.BooleanVar(value=self.config_mgr.get("do_push", True))
        ttk.Checkbutton(
            card_opt, text="📳 푸시 알림 전송",
            variable=self.push_var,
            style="TCheckbutton"
        ).pack(anchor="w", pady=2)
        
        # 예약 옵션
        card_sch = self._make_card(right, "예약 게시")
        
        self.schedule_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            card_sch, text="⏰ 예약 게시 사용",
            variable=self.schedule_var,
            command=self._toggle_schedule_fields
        ).pack(anchor="w", pady=(0, 8))
        
        self.sch_fields_frame = tk.Frame(card_sch, bg=C_WHITE)
        self.sch_fields_frame.pack(fill="x")
        
        tk.Label(self.sch_fields_frame, text="날짜 (YYYY-MM-DD):", bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w")
        self.sch_date_entry = ttk.Entry(self.sch_fields_frame, font=("맑은 고딕", 10))
        self.sch_date_entry.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d"))
        self.sch_date_entry.pack(fill="x", pady=(2, 6))
        
        tk.Label(self.sch_fields_frame, text="시간 (HH:MM):", bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w")
        self.sch_time_entry = ttk.Entry(self.sch_fields_frame, font=("맑은 고딕", 10))
        self.sch_time_entry.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%H:%M"))
        self.sch_time_entry.pack(fill="x", pady=(2, 6))
        
        tk.Label(self.sch_fields_frame, text="반복:", bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w")
        self.repeat_var = tk.StringVar(value="none")
        repeat_combo = ttk.Combobox(
            self.sch_fields_frame, textvariable=self.repeat_var,
            values=["none", "daily", "weekly"], state="readonly"
        )
        repeat_combo.pack(fill="x", pady=(2, 0))
        
        self._toggle_schedule_fields()
        
        # 템플릿 불러오기
        card_tpl = self._make_card(right, "템플릿")
        
        self.tpl_var = tk.StringVar()
        self.tpl_combo = ttk.Combobox(
            card_tpl, textvariable=self.tpl_var,
            state="readonly", font=("맑은 고딕", 9)
        )
        self.tpl_combo.pack(fill="x", pady=(0, 6))
        
        ttk.Button(
            card_tpl, text="불러오기",
            style="Secondary.TButton",
            command=self._load_template
        ).pack(fill="x")
        
        self._refresh_template_combo()
        
        # 게시 버튼
        self.post_btn = ttk.Button(
            right, text="📤 게시물 올리기",
            style="Primary.TButton",
            command=self._on_post_click
        )
        self.post_btn.pack(fill="x", pady=(12, 4))
        
        # 상태 메시지
        self.status_label = tk.Label(
            right, text="",
            bg=C_BG, fg=C_TEXT_L,
            font=("맑은 고딕", 9),
            wraplength=240, justify="left"
        )
        self.status_label.pack(fill="x")
        
        return frame
    
    # ─── 예약 게시 페이지 ────────────────────────────────────
    def _build_schedule_page(self) -> tk.Frame:
        frame = tk.Frame(self.page_container, bg=C_BG)
        
        # 툴바
        toolbar = tk.Frame(frame, bg=C_BG)
        toolbar.pack(fill="x", padx=15, pady=(15, 8))
        
        ttk.Button(
            toolbar, text="🗑️ 선택 삭제",
            style="Danger.TButton",
            command=self._delete_selected_schedule
        ).pack(side="right")
        
        ttk.Button(
            toolbar, text="🔄 새로고침",
            style="Secondary.TButton",
            command=self._refresh_schedule_ui
        ).pack(side="right", padx=(0, 6))
        
        # 예약 목록 테이블
        card = self._make_card(frame, "예약된 게시물")
        
        cols = ("band", "content_preview", "scheduled", "status", "repeat")
        self.schedule_tree = ttk.Treeview(
            card, columns=cols, show="headings", height=16
        )
        
        col_cfg = [
            ("band", "밴드", 130),
            ("content_preview", "내용 미리보기", 280),
            ("scheduled", "예약 시간", 160),
            ("status", "상태", 80),
            ("repeat", "반복", 70),
        ]
        for col_id, heading, width in col_cfg:
            self.schedule_tree.heading(col_id, text=heading)
            self.schedule_tree.column(col_id, width=width, minwidth=60)
        
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.schedule_tree.yview)
        self.schedule_tree.configure(yscrollcommand=scrollbar.set)
        
        self.schedule_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self._refresh_schedule_ui()
        
        return frame
    
    # ─── 템플릿 관리 페이지 ──────────────────────────────────
    def _build_template_page(self) -> tk.Frame:
        frame = tk.Frame(self.page_container, bg=C_BG)
        
        left = tk.Frame(frame, bg=C_BG, width=280)
        left.pack(side="left", fill="y", padx=(15, 8), pady=15)
        left.pack_propagate(False)
        
        right = tk.Frame(frame, bg=C_BG)
        right.pack(side="right", fill="both", expand=True, padx=(0, 15), pady=15)
        
        # ── 왼쪽: 목록 ──
        card_list = self._make_card(left, "템플릿 목록")
        
        self.tpl_listbox = tk.Listbox(
            card_list, font=("맑은 고딕", 10),
            bg="#fafafa", relief="flat",
            selectmode="single", height=18,
        )
        self.tpl_listbox.pack(fill="both", expand=True)
        self.tpl_listbox.bind("<<ListboxSelect>>", self._on_template_select)
        
        btn_row = tk.Frame(card_list, bg=C_WHITE)
        btn_row.pack(fill="x", pady=(6, 0))
        
        ttk.Button(btn_row, text="삭제", style="Danger.TButton",
                   command=self._delete_template).pack(side="right")
        ttk.Button(btn_row, text="새 템플릿", style="Secondary.TButton",
                   command=self._new_template).pack(side="left")
        
        # ── 오른쪽: 편집 ──
        card_edit = self._make_card(right, "템플릿 편집")
        
        tk.Label(card_edit, text="템플릿 이름:", bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w")
        self.tpl_name_entry = ttk.Entry(card_edit, font=("맑은 고딕", 10))
        self.tpl_name_entry.pack(fill="x", pady=(2, 10))
        
        tk.Label(card_edit, text="내용:", bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w")
        self.tpl_content_text = scrolledtext.ScrolledText(
            card_edit, font=("맑은 고딕", 10),
            wrap="word", height=14, relief="flat",
            bg="#fafafa", fg=C_TEXT, padx=8, pady=8,
        )
        self.tpl_content_text.pack(fill="both", expand=True, pady=(2, 0))
        
        ttk.Button(
            card_edit, text="💾 저장",
            style="Primary.TButton",
            command=self._save_template
        ).pack(fill="x", pady=(10, 0))
        
        self._refresh_template_list()
        
        return frame
    
    # ─── 설정 페이지 ─────────────────────────────────────────
    def _build_settings_page(self) -> tk.Frame:
        frame = tk.Frame(self.page_container, bg=C_BG)
        
        content = tk.Frame(frame, bg=C_BG)
        content.pack(fill="both", expand=True, padx=20, pady=15)
        
        # API 설정
        card_api = self._make_card(content, "Band Open API 설정")
        
        self._setting_row(card_api, "Client ID (앱 키):", "client_id_entry",
                          self.config_mgr.get("client_id", ""), show="")
        self._setting_row(card_api, "Client Secret:", "client_secret_entry",
                          self.config_mgr.get("client_secret", ""), show="*")
        
        tk.Label(
            card_api,
            text="💡 Band Developers (developers.band.us) 에서 앱 등록 후 발급받으세요.\n"
                 "   Redirect URI: http://localhost:9988/callback",
            bg=C_WHITE, fg=C_TEXT_L,
            font=("맑은 고딕", 8), justify="left"
        ).pack(anchor="w", pady=(4, 0))
        
        # 인증
        card_auth = self._make_card(content, "인증 관리")
        
        auth_row = tk.Frame(card_auth, bg=C_WHITE)
        auth_row.pack(fill="x", pady=(0, 8))
        
        ttk.Button(
            auth_row, text="🔑 브라우저로 로그인",
            style="Primary.TButton",
            command=self._do_oauth_login
        ).pack(side="left")
        
        ttk.Button(
            auth_row, text="🔓 토큰 직접 입력",
            style="Secondary.TButton",
            command=self._show_token_dialog
        ).pack(side="left", padx=(8, 0))
        
        ttk.Button(
            auth_row, text="✅ 토큰 검증",
            style="Secondary.TButton",
            command=self._verify_token
        ).pack(side="left", padx=(8, 0))
        
        ttk.Button(
            auth_row, text="🚪 로그아웃",
            style="Danger.TButton",
            command=self._logout
        ).pack(side="right")
        
        self.settings_status = tk.Label(
            card_auth, text="",
            bg=C_WHITE, fg=C_TEXT_L,
            font=("맑은 고딕", 9)
        )
        self.settings_status.pack(anchor="w")
        
        # 저장 버튼
        ttk.Button(
            content, text="💾 설정 저장",
            style="Primary.TButton",
            command=self._save_settings
        ).pack(anchor="w", pady=(12, 0))
        
        return frame
    
    # ─── 헬퍼 메서드 ─────────────────────────────────────────
    def _make_card(self, parent, title: str = "") -> tk.Frame:
        """카드 UI 컴포넌트"""
        outer = tk.Frame(parent, bg=C_BG, pady=6)
        outer.pack(fill="x" if parent.winfo_class() != "Frame" else "both",
                   expand=True if title else False)
        
        card = tk.Frame(outer, bg=C_WHITE, bd=0, relief="flat",
                        highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        
        if title:
            tk.Label(
                card, text=title,
                bg=C_WHITE, fg=C_TEXT,
                font=("맑은 고딕", 10, "bold"),
                padx=14, pady=8, anchor="w"
            ).pack(fill="x")
            tk.Frame(card, bg=C_BORDER, height=1).pack(fill="x")
        
        inner = tk.Frame(card, bg=C_WHITE, padx=14, pady=10)
        inner.pack(fill="both", expand=True)
        return inner
    
    def _setting_row(self, parent, label_text, attr_name, default_val, show=""):
        """설정 행 (라벨 + 엔트리)"""
        tk.Label(parent, text=label_text, bg=C_WHITE,
                 font=("맑은 고딕", 9)).pack(anchor="w", pady=(4, 0))
        entry = ttk.Entry(parent, font=("맑은 고딕", 10), show=show)
        entry.insert(0, default_val)
        entry.pack(fill="x", pady=(2, 6))
        setattr(self, attr_name, entry)
    
    def _switch_page(self, page_id: str):
        """페이지 전환"""
        # 이전 페이지 숨기기
        for pid, pframe in self.pages.items():
            pframe.pack_forget()
        
        # 새 페이지 보이기
        self.pages[page_id].pack(fill="both", expand=True)
        self._current_page = page_id
        
        # 사이드바 버튼 스타일 갱신
        titles = {
            "write": "게시물 작성",
            "schedule": "예약 게시",
            "template": "템플릿 관리",
            "settings": "설정",
        }
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(bg=C_PRIMARY, fg=C_WHITE)
            else:
                btn.configure(bg=C_SIDEBAR, fg="#c0c0d8")
        
        self.page_title.configure(text=titles.get(page_id, ""))
        
        # 페이지별 후처리
        if page_id == "schedule":
            self._refresh_schedule_ui()
        elif page_id == "template":
            self._refresh_template_list()
    
    # ─── 밴드 목록 ───────────────────────────────────────────
    def _refresh_bands(self):
        """밴드 목록 새로고침"""
        if not self.api.is_authenticated():
            messagebox.showwarning("인증 필요", "먼저 밴드 계정으로 로그인하세요.\n설정 → 브라우저로 로그인")
            return
        
        def do_fetch():
            try:
                self.set_status("밴드 목록을 불러오는 중...", C_TEXT_L)
                self.bands = self.api.get_bands()
                names = [f"{b['name']} ({b.get('member_count', 0)}명)" for b in self.bands]
                self.band_combo["values"] = names
                if names:
                    self.band_combo.current(0)
                    self._on_band_select(None)
                self.set_status(f"✅ 밴드 {len(self.bands)}개 불러옴", C_SUCCESS)
            except BandAPIError as e:
                self.set_status(f"❌ {e}", C_ERROR)
        
        threading.Thread(target=do_fetch, daemon=True).start()
    
    def _on_band_select(self, event):
        idx = self.band_combo.current()
        if 0 <= idx < len(self.bands):
            self.selected_band = self.bands[idx]
            self.config_mgr.set("last_band_key", self.selected_band["band_key"])
            self.config_mgr.set("last_band_name", self.selected_band["name"])
            self.config_mgr.save()
    
    # ─── 이미지 ──────────────────────────────────────────────
    def _add_image(self):
        paths = filedialog.askopenfilenames(
            title="이미지 선택",
            filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.gif *.webp"), ("모든 파일", "*.*")]
        )
        for p in paths:
            if p not in self.attached_images:
                self.attached_images.append(p)
                self.img_listbox.insert("end", os.path.basename(p))
    
    def _clear_images(self):
        self.attached_images.clear()
        self.img_listbox.delete(0, "end")
    
    # ─── 게시 버튼 ───────────────────────────────────────────
    def _on_post_click(self):
        if not self.api.is_authenticated():
            messagebox.showwarning("인증 필요", "먼저 밴드 계정으로 로그인하세요.")
            return
        if not self.selected_band:
            messagebox.showwarning("밴드 선택", "게시할 밴드를 선택하세요.")
            return
        
        content = self.content_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("내용 없음", "게시물 내용을 입력하세요.")
            return
        
        band_key = self.selected_band["band_key"]
        band_name = self.selected_band["name"]
        do_push = self.push_var.get()
        
        # 예약 게시 여부
        if self.schedule_var.get():
            self._add_schedule(band_key, band_name, content, do_push)
        else:
            self._post_immediately(band_key, content, do_push)
    
    def _post_immediately(self, band_key: str, content: str, do_push: bool):
        """즉시 게시"""
        self.post_btn.state(["disabled"])
        self.set_status("게시 중...", C_TEXT_L)
        
        def do_post():
            try:
                # 이미지 업로드
                photo_keys = []
                for img_path in self.attached_images:
                    try:
                        key = self.api.upload_photo(band_key, img_path)
                        if key:
                            photo_keys.append(key)
                    except BandAPIError as e:
                        print(f"이미지 업로드 실패: {e}")
                
                result = self.api.write_post(band_key, content, do_push, photo_keys or None)
                post_key = result.get("post_key", "")
                
                self.set_status(f"✅ 게시 완료! (post_key: {post_key})", C_SUCCESS)
                self.after(0, lambda: messagebox.showinfo(
                    "게시 완료",
                    f"✅ 게시물이 성공적으로 올라갔습니다!\n"
                    f"밴드: {self.selected_band.get('name')}\n"
                    f"게시물 ID: {post_key}"
                ))
                self.after(0, lambda: self.content_text.delete("1.0", "end"))
                self.after(0, self._clear_images)
            except BandAPIError as e:
                self.set_status(f"❌ 게시 실패: {e}", C_ERROR)
                self.after(0, lambda: messagebox.showerror("게시 실패", str(e)))
            finally:
                self.after(0, lambda: self.post_btn.state(["!disabled"]))
        
        threading.Thread(target=do_post, daemon=True).start()
    
    def _add_schedule(self, band_key: str, band_name: str, content: str, do_push: bool):
        """예약 등록"""
        try:
            date_str = self.sch_date_entry.get().strip()
            time_str = self.sch_time_entry.get().strip()
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
            if dt <= datetime.now():
                messagebox.showwarning("시간 오류", "예약 시간은 현재 시간 이후여야 합니다.")
                return
            
            repeat = self.repeat_var.get()
            post = self.scheduler.add_post(
                band_key, band_name, content, dt,
                do_push, list(self.attached_images), repeat
            )
            
            messagebox.showinfo(
                "예약 완료",
                f"✅ 게시물이 예약되었습니다!\n"
                f"밴드: {band_name}\n"
                f"예약 시간: {dt.strftime('%Y-%m-%d %H:%M')}\n"
                f"반복: {repeat}"
            )
            self.content_text.delete("1.0", "end")
            self._clear_images()
            self.schedule_var.set(False)
            self._toggle_schedule_fields()
            
        except ValueError:
            messagebox.showerror("날짜 형식 오류", "날짜: YYYY-MM-DD, 시간: HH:MM 형식으로 입력하세요.")
    
    def _execute_scheduled_post(self, band_key, content, do_push, image_paths):
        """스케줄러 콜백 - 예약 게시 실행"""
        try:
            photo_keys = []
            for img_path in (image_paths or []):
                try:
                    key = self.api.upload_photo(band_key, img_path)
                    if key:
                        photo_keys.append(key)
                except:
                    pass
            self.api.write_post(band_key, content, do_push, photo_keys or None)
            return True
        except:
            return False
    
    # ─── 예약 UI ─────────────────────────────────────────────
    def _refresh_schedule_ui(self):
        """예약 목록 갱신"""
        def do_refresh():
            for item in self.schedule_tree.get_children():
                self.schedule_tree.delete(item)
            
            status_icon = {"pending": "⏳", "done": "✅", "failed": "❌"}
            repeat_icon = {"none": "1회", "daily": "매일", "weekly": "매주"}
            
            for post in sorted(self.scheduler.get_all_posts(),
                                key=lambda p: p.scheduled_time, reverse=False):
                icon = status_icon.get(post.status, "?")
                self.schedule_tree.insert("", "end",
                    iid=post.post_id,
                    values=(
                        post.band_name,
                        post.content[:50] + "..." if len(post.content) > 50 else post.content,
                        post.scheduled_time.strftime("%Y-%m-%d %H:%M"),
                        f"{icon} {post.status}",
                        repeat_icon.get(post.repeat, post.repeat),
                    )
                )
        self.after(0, do_refresh)
    
    def _delete_selected_schedule(self):
        sel = self.schedule_tree.selection()
        if not sel:
            messagebox.showinfo("선택 없음", "삭제할 예약 게시물을 선택하세요.")
            return
        if messagebox.askyesno("삭제 확인", f"{len(sel)}개의 예약을 삭제할까요?"):
            for iid in sel:
                self.scheduler.remove_post(iid)
            self._refresh_schedule_ui()
    
    # ─── 예약 토글 ────────────────────────────────────────────
    def _toggle_schedule_fields(self):
        state = "normal" if self.schedule_var.get() else "disabled"
        for w in self.sch_fields_frame.winfo_children():
            try:
                w.configure(state=state)
            except:
                pass
    
    # ─── 템플릿 ──────────────────────────────────────────────
    def _refresh_template_list(self):
        if hasattr(self, "tpl_listbox"):
            self.tpl_listbox.delete(0, "end")
            for t in self.config_mgr.get_templates():
                self.tpl_listbox.insert("end", t["name"])
        self._refresh_template_combo()
    
    def _refresh_template_combo(self):
        names = [t["name"] for t in self.config_mgr.get_templates()]
        if hasattr(self, "tpl_combo"):
            self.tpl_combo["values"] = names
    
    def _on_template_select(self, event):
        sel = self.tpl_listbox.curselection()
        if sel:
            name = self.tpl_listbox.get(sel[0])
            content = self.config_mgr.get_template_content(name)
            self.tpl_name_entry.delete(0, "end")
            self.tpl_name_entry.insert(0, name)
            self.tpl_content_text.delete("1.0", "end")
            if content:
                self.tpl_content_text.insert("1.0", content)
    
    def _new_template(self):
        self.tpl_listbox.selection_clear(0, "end")
        self.tpl_name_entry.delete(0, "end")
        self.tpl_content_text.delete("1.0", "end")
        self.tpl_name_entry.focus()
    
    def _save_template(self):
        name = self.tpl_name_entry.get().strip()
        content = self.tpl_content_text.get("1.0", "end-1c").strip()
        if not name:
            messagebox.showwarning("이름 없음", "템플릿 이름을 입력하세요.")
            return
        if not content:
            messagebox.showwarning("내용 없음", "템플릿 내용을 입력하세요.")
            return
        self.config_mgr.add_template(name, content)
        self._refresh_template_list()
        messagebox.showinfo("저장 완료", f"템플릿 '{name}'이 저장되었습니다.")
    
    def _delete_template(self):
        sel = self.tpl_listbox.curselection()
        if not sel:
            messagebox.showinfo("선택 없음", "삭제할 템플릿을 선택하세요.")
            return
        name = self.tpl_listbox.get(sel[0])
        if messagebox.askyesno("삭제 확인", f"템플릿 '{name}'을 삭제할까요?"):
            self.config_mgr.delete_template(name)
            self._refresh_template_list()
    
    def _load_template(self):
        name = self.tpl_var.get()
        if not name:
            return
        content = self.config_mgr.get_template_content(name)
        if content:
            if self.content_text.get("1.0", "end-1c").strip():
                if not messagebox.askyesno("템플릿 불러오기", "현재 내용을 덮어쓸까요?"):
                    return
            self.content_text.delete("1.0", "end")
            self.content_text.insert("1.0", content)
            self._update_char_count(None)
    
    # ─── 설정 저장 ────────────────────────────────────────────
    def _save_settings(self):
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()
        
        self.config_mgr.update({
            "client_id": client_id,
            "client_secret": client_secret,
        })
        
        # API 인스턴스 업데이트
        self.api.client_id = client_id
        self.api.client_secret = client_secret
        
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")
    
    # ─── 인증 ────────────────────────────────────────────────
    def _check_auth_on_startup(self):
        """앱 시작 시 토큰 유효성 확인"""
        if self.api.is_authenticated():
            def check():
                try:
                    profile = self.api.get_profile()
                    name = profile.get("name", "사용자")
                    self._update_auth_status(True, name)
                    self._refresh_bands()
                except:
                    self._update_auth_status(False)
            threading.Thread(target=check, daemon=True).start()
        else:
            self._update_auth_status(False)
    
    def _do_oauth_login(self):
        """OAuth2 로그인"""
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()
        
        if not client_id or not client_secret:
            messagebox.showwarning(
                "앱 키 없음",
                "Client ID와 Client Secret을 먼저 입력하고 저장하세요.\n\n"
                "band.us Developers에서 앱을 등록하면 발급받을 수 있습니다."
            )
            return
        
        self.api.client_id = client_id
        self.api.client_secret = client_secret
        
        self.settings_status.configure(text="🔄 브라우저에서 인증 진행 중...", fg=C_WARNING)
        
        def do_auth():
            try:
                success = self.api.authenticate_with_browser(
                    callback=lambda msg: self.after(0, lambda: 
                        self.settings_status.configure(text=msg, fg=C_WARNING))
                )
                if success:
                    profile = self.api.get_profile()
                    name = profile.get("name", "사용자")
                    # 토큰 저장
                    self.config_mgr.update({"access_token": self.api.access_token})
                    self.after(0, lambda: self._update_auth_status(True, name))
                    self.after(0, lambda: self.settings_status.configure(
                        text=f"✅ {name}님으로 로그인 완료!", fg=C_SUCCESS))
                    self.after(0, self._refresh_bands)
                else:
                    self.after(0, lambda: self.settings_status.configure(
                        text="❌ 인증 실패. 다시 시도하세요.", fg=C_ERROR))
            except BandAPIError as e:
                self.after(0, lambda: self.settings_status.configure(
                    text=f"❌ 오류: {e}", fg=C_ERROR))
        
        threading.Thread(target=do_auth, daemon=True).start()
    
    def _show_token_dialog(self):
        """액세스 토큰 직접 입력 다이얼로그"""
        dialog = tk.Toplevel(self)
        dialog.title("액세스 토큰 입력")
        dialog.geometry("480x180")
        dialog.configure(bg=C_BG)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="액세스 토큰을 직접 붙여넣으세요:",
                 bg=C_BG, font=("맑은 고딕", 10)).pack(padx=20, pady=(15, 5), anchor="w")
        
        entry = ttk.Entry(dialog, font=("맑은 고딕", 10), show="*")
        entry.pack(fill="x", padx=20)
        
        existing = self.config_mgr.get("access_token", "")
        if existing:
            entry.insert(0, existing)
        
        def confirm():
            token = entry.get().strip()
            if token:
                self.api.set_access_token(token)
                self.config_mgr.update({"access_token": token})
                self.settings_status.configure(text="토큰 설정 완료 (검증 버튼으로 확인)", fg=C_WARNING)
                dialog.destroy()
        
        ttk.Button(dialog, text="확인", style="Primary.TButton",
                   command=confirm).pack(pady=12)
    
    def _verify_token(self):
        """토큰 유효성 검증"""
        if not self.api.is_authenticated():
            messagebox.showwarning("토큰 없음", "먼저 토큰을 설정하세요.")
            return
        
        self.settings_status.configure(text="🔄 검증 중...", fg=C_WARNING)
        
        def do_verify():
            try:
                profile = self.api.get_profile()
                name = profile.get("name", "사용자")
                self.after(0, lambda: self._update_auth_status(True, name))
                self.after(0, lambda: self.settings_status.configure(
                    text=f"✅ 유효한 토큰 - {name}님", fg=C_SUCCESS))
            except BandAPIError as e:
                self.after(0, lambda: self._update_auth_status(False))
                self.after(0, lambda: self.settings_status.configure(
                    text=f"❌ 유효하지 않은 토큰: {e}", fg=C_ERROR))
        
        threading.Thread(target=do_verify, daemon=True).start()
    
    def _logout(self):
        if messagebox.askyesno("로그아웃", "로그아웃 하시겠습니까?"):
            self.api.access_token = None
            self.config_mgr.update({"access_token": ""})
            self._update_auth_status(False)
            self.settings_status.configure(text="로그아웃 완료", fg=C_TEXT_L)
            self.bands = []
            self.selected_band = None
            self.band_combo["values"] = []
            self.band_var.set("밴드를 선택하세요")
    
    def _update_auth_status(self, authenticated: bool, username: str = ""):
        def do_update():
            if authenticated:
                self.auth_status_label.configure(text="● 인증됨", fg=C_SUCCESS)
                self.user_name_label.configure(text=username)
            else:
                self.auth_status_label.configure(text="● 미인증", fg=C_ERROR)
                self.user_name_label.configure(text="")
        self.after(0, do_update)
    
    # ─── 유틸 ────────────────────────────────────────────────
    def set_status(self, msg: str, color: str = None):
        def do_set():
            if hasattr(self, "status_label"):
                self.status_label.configure(text=msg, fg=color or C_TEXT_L)
        self.after(0, do_set)
    
    def _update_char_count(self, event):
        content = self.content_text.get("1.0", "end-1c")
        count = len(content)
        self.char_count_label.configure(text=f"{count:,}자")


def main():
    app = NBandWriterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
