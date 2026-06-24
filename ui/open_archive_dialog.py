import enum
import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QMessageBox,
)

from core.archive import Archive
from core.extractor import ExtractResult, Extractor
from core.icons import lucide_icon
from core.language import LanguageManager
from tools.file_utils import human_readable_size


class OpenArchiveChoice(enum.IntEnum):
    CANCEL = 0
    OPEN = 1
    EXTRACT_HERE = 2
    EXTRACT_TO = 3


class _OpenExtractWorker(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(ExtractResult)

    def __init__(self, extractor: Extractor):
        super().__init__()
        self._extractor = extractor

    def run(self):
        res = self._extractor.extract_all(
            progress_callback=lambda c, t: self.progress.emit(c, t),
        )
        self.result.emit(res)


class OpenArchiveDialog(QDialog):
    def __init__(self, archive_path: str, lang: LanguageManager, parent=None):
        super().__init__(parent)
        self._archive_path = archive_path
        self._lang = lang
        self._choice = OpenArchiveChoice.CANCEL
        self._worker = None
        self._setup_ui()
        self._load_archive_info()
        self._retranslate_buttons()

    def _setup_ui(self):
        self.setWindowTitle(self._lang.tr("open_archive_dialog_title", "Open Archive"))
        self.setMinimumWidth(440)
        self.setModal(True)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base_dir, "assets", "icons", "Kouprey Logo Variations.ico")
        if not os.path.isfile(ico):
            ico = os.path.join(base_dir, "assets", "icons", "Kouprey Logo Variations.png")
        if os.path.isfile(ico):
            self.setWindowIcon(QIcon(ico))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        icon_label = QLabel()
        icon_label.setPixmap(lucide_icon("file-archive", 48).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        self._name_label = QLabel()
        self._name_label.setObjectName("titleLabel")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)

        self._info_label = QLabel()
        self._info_label.setObjectName("subtitleLabel")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel()
        self._status_label.setObjectName("captionLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        layout.addSpacing(4)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self._open_btn = QPushButton()
        self._open_btn.setObjectName("accentButton")
        self._open_btn.setMinimumHeight(40)
        self._open_btn.clicked.connect(self._on_open)
        btn_layout.addWidget(self._open_btn)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self._extract_here_btn = QPushButton()
        self._extract_here_btn.setMinimumHeight(36)
        self._extract_here_btn.clicked.connect(self._on_extract_here)
        row1.addWidget(self._extract_here_btn)
        self._extract_to_btn = QPushButton()
        self._extract_to_btn.setMinimumHeight(36)
        self._extract_to_btn.clicked.connect(self._on_extract_to)
        row1.addWidget(self._extract_to_btn)
        btn_layout.addLayout(row1)

        self._cancel_btn = QPushButton()
        self._cancel_btn.setMinimumHeight(36)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    def _load_archive_info(self):
        name = os.path.basename(self._archive_path)
        self._name_label.setText(name)

        try:
            archive = Archive(self._archive_path)
            fmt_name = archive.format.display_name if archive.format else "?"
            count = archive.entry_count
            total = human_readable_size(archive.total_size)
            file_size = human_readable_size(os.path.getsize(self._archive_path))
            self._info_label.setText(
                f"{fmt_name}  ·  {count} {self._lang.tr('entries', 'entries')}  ·  "
                f"{total} ({file_size} on disk)"
            )
        except Exception:
            self._info_label.setText(
                human_readable_size(os.path.getsize(self._archive_path))
            )

    def _retranslate_buttons(self):
        self._open_btn.setText(
            self._lang.tr("dialog_open_viewer", "Open in Viewer")
        )
        self._extract_here_btn.setText(
            self._lang.tr("dialog_extract_here", "Extract Here")
        )
        self._extract_to_btn.setText(
            self._lang.tr("dialog_extract_to", "Extract to Folder")
        )
        self._cancel_btn.setText(
            self._lang.tr("cancel", "Cancel")
        )

    def showEvent(self, event):
        super().showEvent(event)
        self._retranslate_buttons()

    def _set_buttons_enabled(self, enabled: bool):
        self._open_btn.setEnabled(enabled)
        self._extract_here_btn.setEnabled(enabled)
        self._extract_to_btn.setEnabled(enabled)
        self._cancel_btn.setEnabled(enabled)

    def _on_open(self):
        self._choice = OpenArchiveChoice.OPEN
        self.accept()

    def _on_extract_here(self):
        self._choice = OpenArchiveChoice.EXTRACT_HERE
        base = os.path.dirname(os.path.abspath(self._archive_path))
        self._run_extraction(base)

    def _on_extract_to(self):
        self._choice = OpenArchiveChoice.EXTRACT_TO
        base = os.path.dirname(os.path.abspath(self._archive_path))
        name = os.path.splitext(os.path.basename(self._archive_path))[0]
        out_dir = os.path.join(base, name)
        self._run_extraction(out_dir)

    def _run_extraction(self, output_dir: str):
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_label.setVisible(True)
        self._status_label.setText(
            self._lang.tr("extracting", "Extracting") + "..."
        )
        self._set_buttons_enabled(False)

        extractor = Extractor(self._archive_path, output_dir)
        self._worker = _OpenExtractWorker(extractor)
        self._worker.progress.connect(self._on_progress)
        self._worker.result.connect(self._on_extract_result)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)

    def _on_extract_result(self, res: ExtractResult):
        self._progress_bar.setVisible(False)
        self._status_label.setVisible(False)
        self._set_buttons_enabled(True)

        if res.success:
            QMessageBox.information(
                self,
                self._lang.tr("success", "Success"),
                self._lang.tr("dialog_extract_complete",
                              "Extraction complete.\n{count} entries extracted.")
                .format(count=res.extracted_count),
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                self._lang.tr("error", "Error"),
                res.message,
            )
            self._choice = OpenArchiveChoice.CANCEL

    def choice(self) -> OpenArchiveChoice:
        return self._choice
