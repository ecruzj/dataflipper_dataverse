import sys
import os
import json

from common.helper import resolve_current_user_email, resolve_current_environment
from dataverse_apis.core.services.dataverse_client import call_dataverse
from dataverse_apis.core.logging.logging_conf import get_logger, setup_logging
from dataverse_apis.tasks.sharepoint_documents import build_sharepoint_folder_url, get_relativeurls_for_object_id
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PySide6.QtGui import QIcon
from ui.main_window import Ui_MainWindow
from worker_thread import WorkerThread

try:
    from common.build_info import FULL_VERSION, APP_VERSION, BUILD_NUMBER, GIT_SHA
except Exception:
    # fallback if you run without a previous build step
    from common.version import APP_VERSION
    FULL_VERSION, BUILD_NUMBER, GIT_SHA = f"{APP_VERSION}+dev", 0, "nogit"

def resource_path(relative_path):
    """
    Get the path to a resource. If frozen, this will be from the _MEIPASS directory.
    Otherwise, it will be from the current working directory.

    :param relative_path: The path to the resource relative to the current working
        directory or _MEIPASS directory.
    :return: The absolute path to the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(QMainWindow):
    def __init__(self):
        """
        Initialize the main window and set up the UI.

        This function initializes the main window's UI and sets up the connections
        for the buttons at the bottom of the window.
        """
        setup_logging(app_name="dataverse_apis")  # Logging setup
        log = get_logger(__name__)
        log.info("Application started")
        log.info(f"App version: {APP_VERSION}  Build: {BUILD_NUMBER}  Git: {GIT_SHA}")
        
        # INCIDENTS
        # ticket_number = "CAS-106375-K4P3H"
        # incident_endpoint = f"incidents?$filter=ticketnumber eq '{ticket_number}'"
        # incident_result = call_dataverse(incident_endpoint)
        
        # print(json.dumps(incident_result, indent=2))
        
        # object_id = "10a95b6d-8a5e-f011-877b-002248af7cca"
        # relative_urls = get_relativeurls_for_object_id(object_id)
        # print(json.dumps(relative_urls, indent=2))
                            
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(f"Data Flipper with Dataverse APIs — v{FULL_VERSION}")
        self.setWindowIcon(QIcon(resource_path("resources/data_flipper_icon.ico")))
        self.ui.txtOutput.setReadOnly(True)
        self.ui.lblStatus.setText("")
        
        # toggle Export Mode according to Process Type
        self.ui.radioProcDocsOnly.toggled.connect(self._update_sections_visibility)
        self.ui.radioProcTransposeOnly.toggled.connect(self._update_sections_visibility)
        self.ui.radioProcTransposeAndDocs.toggled.connect(self._update_sections_visibility)
        self._update_sections_visibility()  # initial state

        # bottom connections
        self.ui.btnSelectFolder.clicked.connect(self.select_folder)
        self.ui.btnProcess.clicked.connect(self.process_files)
        self.ui.btnOpenOutputFolder.clicked.connect(self.open_output_folder)
        
    def _update_sections_visibility(self):
        transpose_only = self.ui.radioProcTransposeOnly.isChecked()
        docs_only = self.ui.radioProcDocsOnly.isChecked()

        # User Information visible only if NOT "Only Transpose Data"
        self.ui.groupUserInfo.setVisible(not transpose_only)

        # Export Mode hidden when "Get Only Related Documents"
        self.ui.groupExportMode.setVisible(not docs_only)

        # Fill in info if the group is visible
        if not transpose_only:
            email = os.getenv("USERNAME", "") or resolve_current_user_email()
            username_text = f"User: {email}" if email else "User: (not detected)"
            env = os.getenv("DATAVERSE_BASE_URI", "")
            env_text = f"Environment: {env}" if env else "Environment: (not detected)"
            self.ui.lblUserValue.setText(username_text)
            self.ui.lblEnvValue.setText(env_text)

    def select_folder(self):
        """
        Open a file dialog to select a folder containing input files.

        When the dialog is closed, the path to the selected folder is set in the
        text box.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.ui.txtFolderPath.setText(folder_path)

    def set_processing_state(self, processing: bool):
        """
        Enable or disable the select folder, process and open output folder buttons
        depending on whether processing is occurring or not.

        Also, add a timestamped message to the output text box indicating whether
        processing has started or finished.

        :param processing: Whether processing is occurring or not.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ui.btnSelectFolder.setEnabled(not processing)
        self.ui.btnProcess.setEnabled(not processing)
        self.ui.btnOpenOutputFolder.setEnabled(not processing)
        if processing:
            self.ui.txtOutput.append(f"⏳ Processing started at {timestamp}\n")
        else:
            self.ui.txtOutput.append(f"✅ Processing finished at {timestamp}\n")
        QApplication.processEvents()

    def process_files(self):
        folder_path = self.ui.txtFolderPath.text().strip()
        self.ui.txtOutput.clear()
        self.ui.progressBar.setValue(0)
        self.ui.lblStatus.setText("")

        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.critical(self, "Error", "Please select a valid folder.")
            return

        # Detect export mode
        if self.ui.radioSeparate.isChecked():
            export_mode = "separate"
        elif self.ui.radioCombined.isChecked():
            export_mode = "combined"
        else:
            export_mode = "per_excel"
            
        # Process Type [SharePoint Documents]
        if self.ui.radioProcTransposeOnly.isChecked():
            process_type = "transpose_only"
        elif self.ui.radioProcTransposeAndDocs.isChecked():
            process_type = "transpose_and_docs"
        else:
            process_type = "docs_only"

        self.set_processing_state(True)

        self.worker = WorkerThread(folder_path, export_mode, process_type)
        self.worker.progress_updated.connect(self.ui.progressBar.setValue)
        self.worker.log_updated.connect(self.ui.txtOutput.append)
        # self.worker.log_pdf_update.connect(self.ui.lblStatus.setText)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, success, errors):
        self.set_processing_state(False)
        self.ui.lblStatus.setText("✅ Completed.")
        if errors:
            QMessageBox.warning(self, "Completed with Errors", "Some issues occurred:\n\n" + "\n".join(errors[-3:]))
        else:
            QMessageBox.information(self, "Success", "✅ All files processed successfully!")
        self.ui.txtOutput.append("🎉 Finished processing all files.\n")

    def open_output_folder(self):
        output_dir = os.path.abspath("output")
        os.startfile(output_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("resources/data_flipper_icon.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())