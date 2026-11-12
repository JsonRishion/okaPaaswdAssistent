import json
import os
import sys

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import config as config_mod
from core import generate as gen_mod
from core import i18n
from core import llm as llm_mod
from core import probe, providers, settings as settings_mod
from core import store as store_mod
from core import version
from core.rules import PasswordRules, infer_from_payload

AI_TIMEOUT = 45
AI_RETRIES = 1


def _assets_dir():
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "assets"))
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "assets"))
        candidates.append(os.path.join(exe_dir, "_internal", "assets"))
    candidates.append(os.path.join(ROOT, "assets"))
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return candidates[0]


ASSETS = _assets_dir()

HEAD_QSS = "color:#eaf2ff;font-size:26px;font-weight:700;background:transparent;"
SUB_QSS = "color:#bcd0e8;font-size:14px;background:transparent;"
LABEL_QSS = "color:#d7e3f4;font-size:13px;background:transparent;"
WARN_QSS = "color:#ffd27f;font-size:13px;background:transparent;"
OK_QSS = "color:#9ff0b0;font-size:13px;background:transparent;"
INPUT_QSS = (
    "QLineEdit,QPlainTextEdit,QComboBox{color:#eaf2ff;background:rgba(12,20,32,0.85);"
    "border:1px solid rgba(255,255,255,0.25);border-radius:8px;padding:6px;}"
)
BACK_QSS = (
    "QPushButton{color:#eaf2ff;font-size:14px;padding:8px 14px;border-radius:10px;"
    "border:1px solid rgba(255,255,255,0.35);background:rgba(255,255,255,0.08);}"
    "QPushButton:hover{background:rgba(255,255,255,0.18);}"
)
PRIMARY_QSS = (
    "QPushButton{color:#04121f;font-size:14px;font-weight:600;padding:9px 16px;"
    "border-radius:10px;background:#7fd1ff;border:none;}"
    "QPushButton:hover{background:#a3dcff;}"
)
CANCEL_QSS = (
    "QPushButton{color:#fff;font-size:14px;font-weight:600;padding:9px 16px;"
    "border-radius:10px;background:#c0504d;border:none;}"
    "QPushButton:hover{background:#d5605d;}"
)
CARD_QSS = (
    "QPushButton{color:#eaf2ff;font-size:18px;font-weight:600;padding:18px;"
    "border:1px solid rgba(255,255,255,0.28);border-radius:16px;"
    "background-color:rgba(20,32,48,0.55);}"
    "QPushButton:hover{background-color:rgba(40,70,110,0.75);"
    "border:1px solid rgba(255,255,255,0.55);}"
)


class AnalyzeWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, context):
        super().__init__()
        self.context = context

    def run(self):
        try:
            result = llm_mod.analyze(self.context, timeout=AI_TIMEOUT, retries=AI_RETRIES)
            self.done.emit(result)
        except Exception as error:
            self.failed.emit("{}: {}".format(type(error).__name__, error))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        settings = settings_mod.load_settings()
        i18n.set_language(settings.language)
        self.setWindowTitle("{} {}".format(i18n.t("app_name"), version.VERSION))
        icon = os.path.join(ASSETS, "logo_color.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1000, 640)
        self.setMinimumSize(860, 560)

        path = os.path.join(ASSETS, "bg_blur.png")
        if not os.path.exists(path):
            path = os.path.join(ASSETS, "bg.jpg")
        self._pix = QPixmap(path) if os.path.exists(path) else QPixmap()

        self.rules = PasswordRules()
        self.password = ""
        self.current_url = ""
        self.probed = False
        self._ai_ok = False
        self._analyzing = False
        self._cancelled = False
        self._elapsed = 0
        self.worker = None

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

        self._build_pages()
        self._load_settings_into_form()
        self._refresh_service()
        if not settings_mod.SETTINGS_PATH.exists():
            self.stack.setCurrentIndex(4)

    def _build_pages(self):
        self.stack.addWidget(self._home())
        self.stack.addWidget(self._probe_page())
        self.stack.addWidget(self._generate_page())
        self.stack.addWidget(self._save_page())
        self.stack.addWidget(self._settings_page())

    def _rebuild_ui(self):
        index = self.stack.currentIndex()
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self._build_pages()
        self._load_settings_into_form()
        self._refresh_service()
        self.stack.setCurrentIndex(min(index, self.stack.count() - 1))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._pix.isNull():
            scaled = self._pix.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            painter.drawPixmap(
                (self.width() - scaled.width()) // 2,
                (self.height() - scaled.height()) // 2,
                scaled,
            )
        else:
            painter.fillRect(self.rect(), QColor("#1b2430"))
        painter.fillRect(self.rect(), QColor(10, 16, 24, 165))
        painter.end()

    def _title_bar(self, title, back_index=0):
        bar = QHBoxLayout()
        back = QPushButton(i18n.t("back"))
        back.setCursor(Qt.PointingHandCursor)
        back.setFixedWidth(120)
        back.setStyleSheet(BACK_QSS)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(back_index))
        heading = QLabel(title)
        heading.setStyleSheet(HEAD_QSS)
        bar.addWidget(back)
        bar.addSpacing(12)
        bar.addWidget(heading)
        bar.addStretch(1)
        return bar

    def _home(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        col = QVBoxLayout(page)
        col.setContentsMargins(48, 40, 48, 40)
        col.setSpacing(18)

        top = QHBoxLayout()
        top.addStretch(1)
        settings_btn = QPushButton(i18n.t("settings_btn"))
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet(BACK_QSS)
        settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        top.addWidget(settings_btn)
        col.addLayout(top)

        title = QLabel(i18n.t("app_name"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(HEAD_QSS)
        subtitle = QLabel(i18n.t("home_subtitle"))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(SUB_QSS)
        col.addWidget(title)
        col.addWidget(subtitle)

        self.service_label = QLabel("")
        self.service_label.setAlignment(Qt.AlignCenter)
        self.service_label.setWordWrap(True)
        col.addWidget(self.service_label)
        col.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(24)
        for key, index in [("card_probe", 1), ("card_gen", 2), ("card_save", 3)]:
            card = QPushButton(i18n.t(key))
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumHeight(170)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            card.setStyleSheet(CARD_QSS)
            card.clicked.connect(lambda _c=False, i=index: self.stack.setCurrentIndex(i))
            row.addWidget(card)
        col.addLayout(row)
        col.addStretch(1)
        return page

    def _probe_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        col = QVBoxLayout(page)
        col.setContentsMargins(32, 24, 32, 24)
        col.setSpacing(10)
        col.addLayout(self._title_bar(i18n.t("probe_title")))

        bar = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(i18n.t("url_ph"))
        self.url_edit.setStyleSheet(INPUT_QSS)
        open_btn = QPushButton(i18n.t("open_btn"))
        open_btn.setStyleSheet(PRIMARY_QSS)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self._open_url)
        bar.addWidget(self.url_edit, 1)
        bar.addWidget(open_btn)
        col.addLayout(bar)

        self.view = QWebEngineView()
        self.view.setMinimumHeight(240)
        col.addWidget(self.view, 3)

        actions = QHBoxLayout()
        self.analyze_btn = QPushButton(i18n.t("analyze_btn"))
        self.analyze_btn.setStyleSheet(PRIMARY_QSS)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._analyze)
        self.probe_status = QLabel("")
        self.probe_status.setStyleSheet(LABEL_QSS)
        self.probe_status.setWordWrap(True)
        actions.addWidget(self.analyze_btn)
        actions.addWidget(self.probe_status, 1)
        col.addLayout(actions)

        self.rules_edit = QPlainTextEdit()
        self.rules_edit.setStyleSheet(INPUT_QSS)
        self.rules_edit.setPlaceholderText(i18n.t("rules_ph"))
        self.rules_edit.setMaximumHeight(120)
        col.addWidget(self.rules_edit)
        return page

    def _open_url(self):
        url = self.url_edit.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        self.view.setUrl(QUrl(url))

    def _refresh_service(self):
        status = llm_mod.backend_status(timeout=2)
        self._ai_ok = status["available"]
        if status["available"]:
            self.service_label.setText(i18n.t("svc_ready"))
            self.service_label.setStyleSheet(OK_QSS)
            return
        others = providers.detect_backends(timeout=1)
        extra = ""
        if others:
            extra = i18n.t("svc_detected_prefix") + "、".join(
                item["name"] for item in others
            ) + i18n.t("svc_detected_suffix")
        self.service_label.setText(i18n.t("svc_not_ready") + extra)
        self.service_label.setStyleSheet(WARN_QSS)

    def _analyze(self):
        if self._analyzing:
            self._cancel_analyze()
            return
        self._refresh_service()
        self._cancelled = False
        self.probe_status.setText(i18n.t("st_fetching"))
        self.view.page().runJavaScript(probe.COLLECT_JS, self._on_collected)

    def _on_collected(self, result):
        try:
            payload = json.loads(result) if result else {}
        except (TypeError, json.JSONDecodeError):
            payload = {}
        fields = payload.get("fields") or []
        if not fields:
            self.probe_status.setText(i18n.t("st_no_field"))
            return
        self.current_url = payload.get("url") or self.url_edit.text().strip()
        self.probed = True
        self.rules = infer_from_payload(payload)
        self.rules_edit.setPlainText(
            json.dumps(self.rules.to_dict(), ensure_ascii=False, indent=2)
        )
        if not self._ai_ok:
            self.probe_status.setText(i18n.t("st_heuristic"))
            return
        self._start_worker(probe.build_context(payload)[0])

    def _start_worker(self, context):
        self._analyzing = True
        self._elapsed = 0
        self.analyze_btn.setText(i18n.t("cancel_btn"))
        self.analyze_btn.setStyleSheet(CANCEL_QSS)
        self.probe_status.setText(i18n.t("st_analyzing", n=0))
        self._timer.start()
        self.worker = AnalyzeWorker(context)
        self.worker.done.connect(self._on_analyzed)
        self.worker.failed.connect(self._on_analyze_failed)
        self.worker.start()

    def _tick(self):
        self._elapsed += 1
        self.probe_status.setText(i18n.t("st_analyzing_hint", n=self._elapsed))

    def _finish_analyze(self, text):
        self._analyzing = False
        self._timer.stop()
        self.analyze_btn.setText(i18n.t("analyze_btn"))
        self.analyze_btn.setStyleSheet(PRIMARY_QSS)
        self.probe_status.setText(text)
        self._refresh_service()

    def _cancel_analyze(self):
        self._cancelled = True
        if self.worker is not None:
            try:
                self.worker.done.disconnect()
                self.worker.failed.disconnect()
            except (RuntimeError, TypeError):
                pass
        self._finish_analyze(i18n.t("st_cancelled"))

    def _on_analyzed(self, rules):
        if self._cancelled:
            return
        if rules is not None:
            self.rules = rules
            self.rules_edit.setPlainText(
                json.dumps(rules.to_dict(), ensure_ascii=False, indent=2)
            )
            self._finish_analyze(i18n.t("st_done_ai"))
        else:
            self._finish_analyze(i18n.t("st_ai_empty"))

    def _on_analyze_failed(self, message):
        if self._cancelled:
            return
        lowered = message.lower()
        if "timed out" in lowered or "timeout" in lowered:
            friendly = i18n.t("st_timeout")
        elif "10061" in message or "refused" in lowered or "connection" in lowered:
            friendly = i18n.t("st_conn")
        else:
            friendly = i18n.t("st_fail_generic", msg=message)
        self._finish_analyze(friendly + i18n.t("st_kept_suffix"))

    def _rules_from_edit(self):
        try:
            data = json.loads(self.rules_edit.toPlainText() or "{}")
            return PasswordRules.from_dict(data)
        except json.JSONDecodeError:
            return self.rules

    def _generate_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        col = QVBoxLayout(page)
        col.setContentsMargins(32, 24, 32, 24)
        col.setSpacing(12)
        col.addLayout(self._title_bar(i18n.t("gen_title")))

        note = QLabel(i18n.t("gen_note"))
        note.setStyleSheet(LABEL_QSS)
        note.setWordWrap(True)
        col.addWidget(note)

        self.gen_rules_edit = QPlainTextEdit()
        self.gen_rules_edit.setStyleSheet(INPUT_QSS)
        self.gen_rules_edit.setMaximumHeight(160)
        col.addWidget(self.gen_rules_edit, 1)

        row = QHBoxLayout()
        row.addWidget(self._label(i18n.t("gen_len")))
        self.gen_length = QLineEdit()
        self.gen_length.setStyleSheet(INPUT_QSS)
        self.gen_length.setFixedWidth(90)
        gen_btn = QPushButton(i18n.t("gen_btn"))
        gen_btn.setStyleSheet(PRIMARY_QSS)
        gen_btn.setCursor(Qt.PointingHandCursor)
        gen_btn.clicked.connect(self._generate)
        row.addWidget(self.gen_length)
        row.addWidget(gen_btn)
        row.addStretch(1)
        col.addLayout(row)

        out_row = QHBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setStyleSheet(INPUT_QSS)
        self.password_edit.setReadOnly(True)
        copy_btn = QPushButton(i18n.t("copy_btn"))
        copy_btn.setStyleSheet(BACK_QSS)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_password)
        out_row.addWidget(self.password_edit, 1)
        out_row.addWidget(copy_btn)
        col.addLayout(out_row)

        self.gen_status = QLabel("")
        self.gen_status.setStyleSheet(WARN_QSS)
        self.gen_status.setWordWrap(True)
        col.addWidget(self.gen_status)
        return page

    def _label(self, text):
        label = QLabel(text)
        label.setStyleSheet(LABEL_QSS)
        return label

    def _generate(self):
        if not self.probed:
            self.password = ""
            self.password_edit.clear()
            self.gen_status.setText(i18n.t("gen_need_probe"))
            return
        rules = self._rules_from_edit()
        length_text = self.gen_length.text().strip()
        length = int(length_text) if length_text.isdigit() else None
        self.password = gen_mod.generate_password(rules, length=length)
        self.password_edit.setText(self.password)
        if self.auto_save_check.isChecked():
            url = self.save_url.text().strip() or self.current_url
            path = store_mod.save_password(
                url,
                self.password,
                rules,
                username=self.save_user.text().strip(),
                directory=self._current_save_dir(),
            )
            self.gen_status.setText(i18n.t("gen_autosaved", p=path))
        else:
            self.gen_status.setText(i18n.t("gen_generated"))

    def _copy_password(self):
        QApplication.clipboard().setText(self.password_edit.text())

    def _save_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        col = QVBoxLayout(page)
        col.setContentsMargins(32, 24, 32, 24)
        col.setSpacing(12)
        col.addLayout(self._title_bar(i18n.t("save_title")))

        self.auto_save_check = QCheckBox(i18n.t("save_auto"))
        self.auto_save_check.setStyleSheet(
            "color:#eaf2ff;font-size:14px;background:transparent;"
        )
        self.auto_save_check.toggled.connect(self._persist_save_prefs)
        col.addWidget(self.auto_save_check)

        col.addWidget(self._label(i18n.t("save_dir_label")))
        dir_row = QHBoxLayout()
        self.save_dir_edit = QLineEdit()
        self.save_dir_edit.setStyleSheet(INPUT_QSS)
        self.save_dir_edit.editingFinished.connect(self._persist_save_prefs)
        browse_btn = QPushButton(i18n.t("browse"))
        browse_btn.setStyleSheet(BACK_QSS)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._choose_dir)
        dir_row.addWidget(self.save_dir_edit, 1)
        dir_row.addWidget(browse_btn)
        col.addLayout(dir_row)

        col.addWidget(self._label(i18n.t("url_label")))
        self.save_url = QLineEdit()
        self.save_url.setStyleSheet(INPUT_QSS)
        col.addWidget(self.save_url)

        col.addWidget(self._label(i18n.t("user_label")))
        self.save_user = QLineEdit()
        self.save_user.setStyleSheet(INPUT_QSS)
        col.addWidget(self.save_user)

        col.addWidget(self._label(i18n.t("pass_label")))
        self.save_password = QLineEdit()
        self.save_password.setStyleSheet(INPUT_QSS)
        col.addWidget(self.save_password)

        save_btn = QPushButton(i18n.t("save_btn"))
        save_btn.setStyleSheet(PRIMARY_QSS)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        col.addWidget(save_btn, 0, Qt.AlignLeft)

        self.save_status = QLabel("")
        self.save_status.setStyleSheet(LABEL_QSS)
        self.save_status.setWordWrap(True)
        col.addWidget(self.save_status)
        col.addStretch(1)
        return page

    def _choose_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self, i18n.t("save_dir_label"), self._current_save_dir()
        )
        if chosen:
            self.save_dir_edit.setText(chosen)
            self._persist_save_prefs()

    def _current_save_dir(self):
        return self.save_dir_edit.text().strip() or settings_mod.DEFAULT_SAVE_DIR

    def _persist_save_prefs(self):
        settings = settings_mod.load_settings()
        settings.auto_save = self.auto_save_check.isChecked()
        settings.save_dir = self._current_save_dir()
        settings_mod.save_settings(settings)

    def _save(self):
        rules = self._rules_from_edit()
        url = self.save_url.text().strip() or self.current_url
        self.save_url.setText(url)
        path = store_mod.save_password(
            url,
            self.save_password.text(),
            rules,
            username=self.save_user.text().strip(),
            directory=self._current_save_dir(),
        )
        self.save_status.setText(i18n.t("save_done", p=path))
        self._persist_save_prefs()

    def _settings_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        col = QVBoxLayout(page)
        col.setContentsMargins(32, 24, 32, 24)
        col.setSpacing(10)
        col.addLayout(self._title_bar(i18n.t("set_title")))

        self.lang_combo = QComboBox()
        self.lang_combo.setStyleSheet(INPUT_QSS)
        for code, label in i18n.LANGUAGES:
            self.lang_combo.addItem(label, code)
        lang_row = QHBoxLayout()
        lang_row.addWidget(self._label(i18n.t("lang_label")))
        lang_row.addWidget(self.lang_combo, 1)
        col.addLayout(lang_row)

        self.radio_builtin = QRadioButton(i18n.t("set_builtin"))
        self.radio_detect = QRadioButton(i18n.t("set_detect"))
        self.radio_manual = QRadioButton(i18n.t("set_manual"))
        for radio in (self.radio_builtin, self.radio_detect, self.radio_manual):
            radio.setStyleSheet("color:#eaf2ff;font-size:14px;background:transparent;")
            col.addWidget(radio)

        col.addWidget(self._label(i18n.t("builtin_label")))
        self.builtin_combo = QComboBox()
        self.builtin_combo.setStyleSheet(INPUT_QSS)
        for model_id in config_mod.BUILTIN_MODELS:
            self.builtin_combo.addItem(model_id, model_id)
        col.addWidget(self.builtin_combo)

        detect_row = QHBoxLayout()
        detect_btn = QPushButton(i18n.t("scan_btn"))
        detect_btn.setStyleSheet(BACK_QSS)
        detect_btn.setCursor(Qt.PointingHandCursor)
        detect_btn.clicked.connect(self._scan)
        self.detect_combo = QComboBox()
        self.detect_combo.setStyleSheet(INPUT_QSS)
        detect_row.addWidget(detect_btn)
        detect_row.addWidget(self.detect_combo, 1)
        col.addLayout(detect_row)

        col.addWidget(self._label(i18n.t("base_url")))
        self.set_base = QLineEdit()
        self.set_base.setStyleSheet(INPUT_QSS)
        col.addWidget(self.set_base)
        col.addWidget(self._label(i18n.t("model_id")))
        self.set_model = QLineEdit()
        self.set_model.setStyleSheet(INPUT_QSS)
        col.addWidget(self.set_model)
        col.addWidget(self._label(i18n.t("api_key")))
        self.set_key = QLineEdit()
        self.set_key.setStyleSheet(INPUT_QSS)
        self.set_key.setEchoMode(QLineEdit.Password)
        col.addWidget(self.set_key)

        save_btn = QPushButton(i18n.t("save_settings"))
        save_btn.setStyleSheet(PRIMARY_QSS)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        col.addWidget(save_btn, 0, Qt.AlignLeft)

        self.settings_status = QLabel("")
        self.settings_status.setStyleSheet(LABEL_QSS)
        self.settings_status.setWordWrap(True)
        col.addWidget(self.settings_status)
        col.addStretch(1)
        return page

    def _scan(self):
        self.detect_combo.clear()
        found = providers.detect_backends(timeout=2)
        for item in found:
            self.detect_combo.addItem(
                "{} — {}".format(item["name"], item["base_url"]), item
            )
        if not found:
            self.detect_combo.addItem("—", None)
        assistants = providers.detect_assistants()
        names = "、".join(item["name"] for item in assistants) or "—"
        self.settings_status.setText(i18n.t("assistants_prefix", n=names))

    def _load_settings_into_form(self):
        settings = settings_mod.load_settings()
        backend = settings.backend
        self.set_base.setText(backend.base_url)
        self.set_model.setText(backend.model)
        self.set_key.setText(backend.api_key)
        if backend.kind == "fcc":
            self.radio_builtin.setChecked(True)
        elif backend.kind == "custom":
            self.radio_manual.setChecked(True)
        else:
            self.radio_detect.setChecked(True)
        builtin_index = self.builtin_combo.findData(backend.model)
        if builtin_index >= 0:
            self.builtin_combo.setCurrentIndex(builtin_index)
        lang_index = self.lang_combo.findData(settings.language)
        if lang_index >= 0:
            self.lang_combo.setCurrentIndex(lang_index)
        self.auto_save_check.blockSignals(True)
        self.auto_save_check.setChecked(settings.auto_save)
        self.auto_save_check.blockSignals(False)
        self.save_dir_edit.setText(settings.save_dir)

    def _save_settings(self):
        if self.radio_builtin.isChecked():
            backend = settings_mod.BackendConfig(
                model=self.builtin_combo.currentData() or config_mod.MODEL
            )
        elif self.radio_manual.isChecked():
            backend = settings_mod.BackendConfig(
                kind="custom",
                name="Custom",
                base_url=self.set_base.text().strip(),
                model=self.set_model.text().strip(),
                api_key=self.set_key.text().strip(),
            )
        else:
            item = self.detect_combo.currentData()
            if not item:
                self.settings_status.setText(i18n.t("set_pick_local"))
                return
            backend = settings_mod.BackendConfig(
                kind=item["kind"],
                name=item["name"],
                base_url=item["base_url"],
                model=self.set_model.text().strip(),
                api_key=self.set_key.text().strip(),
            )
        language = self.lang_combo.currentData() or i18n.DEFAULT_LANGUAGE
        settings_mod.save_settings(
            settings_mod.AppSettings(
                backend=backend,
                auto_save=self.auto_save_check.isChecked(),
                save_dir=self._current_save_dir(),
                language=language,
            )
        )
        self.settings_status.setText(
            i18n.t("set_saved", n=backend.name, u=backend.base_url)
        )
        if language != i18n.current():
            i18n.set_language(language)
            self.setWindowTitle("{} {}".format(i18n.t("app_name"), version.VERSION))
            self._rebuild_ui()


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
