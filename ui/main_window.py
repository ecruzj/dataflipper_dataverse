# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar,
    QPushButton, QRadioButton, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(509, 633)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelFolder = QLabel(self.centralwidget)
        self.labelFolder.setObjectName(u"labelFolder")

        self.verticalLayout.addWidget(self.labelFolder)

        self.horizontalLayoutPath = QHBoxLayout()
        self.horizontalLayoutPath.setObjectName(u"horizontalLayoutPath")
        self.txtFolderPath = QLineEdit(self.centralwidget)
        self.txtFolderPath.setObjectName(u"txtFolderPath")

        self.horizontalLayoutPath.addWidget(self.txtFolderPath)

        self.btnSelectFolder = QPushButton(self.centralwidget)
        self.btnSelectFolder.setObjectName(u"btnSelectFolder")

        self.horizontalLayoutPath.addWidget(self.btnSelectFolder)


        self.verticalLayout.addLayout(self.horizontalLayoutPath)

        self.groupProcess = QGroupBox(self.centralwidget)
        self.groupProcess.setObjectName(u"groupProcess")
        self.verticalLayoutProcess = QVBoxLayout(self.groupProcess)
        self.verticalLayoutProcess.setObjectName(u"verticalLayoutProcess")
        self.radioProcTransposeOnly = QRadioButton(self.groupProcess)
        self.radioProcTransposeOnly.setObjectName(u"radioProcTransposeOnly")
        self.radioProcTransposeOnly.setChecked(True)

        self.verticalLayoutProcess.addWidget(self.radioProcTransposeOnly)

        self.radioProcTransposeAndDocs = QRadioButton(self.groupProcess)
        self.radioProcTransposeAndDocs.setObjectName(u"radioProcTransposeAndDocs")

        self.verticalLayoutProcess.addWidget(self.radioProcTransposeAndDocs)

        self.radioProcDocsOnly = QRadioButton(self.groupProcess)
        self.radioProcDocsOnly.setObjectName(u"radioProcDocsOnly")

        self.verticalLayoutProcess.addWidget(self.radioProcDocsOnly)

        self.groupUserInfo = QGroupBox(self.groupProcess)
        self.groupUserInfo.setObjectName(u"groupUserInfo")
        self.groupUserInfo.setVisible(False)
        self.gridUserInfo = QGridLayout(self.groupUserInfo)
        self.gridUserInfo.setObjectName(u"gridUserInfo")
        self.lblUserValue = QLabel(self.groupUserInfo)
        self.lblUserValue.setObjectName(u"lblUserValue")

        self.gridUserInfo.addWidget(self.lblUserValue, 0, 0, 1, 1)

        self.lblEnvValue = QLabel(self.groupUserInfo)
        self.lblEnvValue.setObjectName(u"lblEnvValue")

        self.gridUserInfo.addWidget(self.lblEnvValue, 1, 0, 1, 1)


        self.verticalLayoutProcess.addWidget(self.groupUserInfo)


        self.verticalLayout.addWidget(self.groupProcess)

        self.groupExportMode = QGroupBox(self.centralwidget)
        self.groupExportMode.setObjectName(u"groupExportMode")
        self.vboxLayout = QVBoxLayout(self.groupExportMode)
        self.vboxLayout.setObjectName(u"vboxLayout")
        self.radioSeparate = QRadioButton(self.groupExportMode)
        self.radioSeparate.setObjectName(u"radioSeparate")
        self.radioSeparate.setChecked(True)

        self.vboxLayout.addWidget(self.radioSeparate)

        self.radioCombined = QRadioButton(self.groupExportMode)
        self.radioCombined.setObjectName(u"radioCombined")

        self.vboxLayout.addWidget(self.radioCombined)

        self.radioPerFile = QRadioButton(self.groupExportMode)
        self.radioPerFile.setObjectName(u"radioPerFile")

        self.vboxLayout.addWidget(self.radioPerFile)


        self.verticalLayout.addWidget(self.groupExportMode)

        self.btnProcess = QPushButton(self.centralwidget)
        self.btnProcess.setObjectName(u"btnProcess")

        self.verticalLayout.addWidget(self.btnProcess)

        self.txtOutput = QTextEdit(self.centralwidget)
        self.txtOutput.setObjectName(u"txtOutput")
        self.txtOutput.setReadOnly(True)

        self.verticalLayout.addWidget(self.txtOutput)

        self.progressBar = QProgressBar(self.centralwidget)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)

        self.verticalLayout.addWidget(self.progressBar)

        self.lblStatus = QLabel(self.centralwidget)
        self.lblStatus.setObjectName(u"lblStatus")
        self.lblStatus.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.lblStatus)

        self.btnOpenOutputFolder = QPushButton(self.centralwidget)
        self.btnOpenOutputFolder.setObjectName(u"btnOpenOutputFolder")

        self.verticalLayout.addWidget(self.btnOpenOutputFolder)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Data Flipper", None))
        self.labelFolder.setText(QCoreApplication.translate("MainWindow", u"Select Main Folder:", None))
        self.btnSelectFolder.setText(QCoreApplication.translate("MainWindow", u"Browse...", None))
        self.groupProcess.setTitle(QCoreApplication.translate("MainWindow", u"Process Type", None))
        self.radioProcTransposeOnly.setText(QCoreApplication.translate("MainWindow", u"Only Transpose Data", None))
        self.radioProcTransposeAndDocs.setText(QCoreApplication.translate("MainWindow", u"Transpose Data and Get Related Documents from Sharepoint", None))
        self.radioProcDocsOnly.setText(QCoreApplication.translate("MainWindow", u"Get Only Related Documents from Sharepoint", None))
        self.groupUserInfo.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.lblUserValue.setText("")
        self.lblEnvValue.setText("")
        self.groupExportMode.setTitle(QCoreApplication.translate("MainWindow", u"Export Mode", None))
        self.radioSeparate.setText(QCoreApplication.translate("MainWindow", u"Separate PDFs (one per sheet)", None))
        self.radioCombined.setText(QCoreApplication.translate("MainWindow", u"Single Combined PDF", None))
        self.radioPerFile.setText(QCoreApplication.translate("MainWindow", u"PDF by Excel file", None))
        self.btnProcess.setText(QCoreApplication.translate("MainWindow", u"Process Files", None))
        self.lblStatus.setText("")
        self.btnOpenOutputFolder.setText(QCoreApplication.translate("MainWindow", u"Open Output Folder", None))
    # retranslateUi

