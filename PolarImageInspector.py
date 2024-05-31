import sys
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QMainWindow,
    QAction,
    QGridLayout,
    QLineEdit,
    QToolTip,
    QScrollArea,
    QFormLayout,
    QGroupBox,
    QPushButton,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import qdarktheme
from Wamos2.polar_image import PolarImage
from PIL import Image
import json
import pathlib


class PolarImageInspector(QMainWindow):
    def __init__(self):
        super().__init__()

        self.polarImage = None
        self.data_dict = {}
        self.pixmap = None

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Polar Image Inspector")
        self.setGeometry(100, 100, 1200, 800)

        # Create a QLabel to display the image
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.resizeEvent = self.customResizeEvent

        # Create a menu bar
        menubar = self.menuBar()

        # Create a File menu
        file_menu = menubar.addMenu("File")

        # Create actions for the File menu
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)

        # Create a layout for the general information
        self.general_info_label = QLabel(self)
        self.general_layout = QHBoxLayout()
        self.general_layout.addWidget(self.general_info_label)

        # Create a group box for general information
        general_group_box = QGroupBox("General Information")
        general_group_box.setLayout(self.general_layout)

        # Create a layout for the image display
        image_layout = QVBoxLayout()
        image_layout.addWidget(general_group_box)
        image_layout.addWidget(self.image_label)

        # Create a widget to hold the image display layout
        image_widget = QWidget()
        image_widget.setLayout(image_layout)

        # Create layout for location information
        self.location_layout = QGridLayout()

        # Create a group box for location information
        location_group_box = QGroupBox("Location Information")
        location_group_box.setLayout(self.location_layout)

        # Create a grid layout for environmental information
        self.environmental_layout = QGridLayout()

        # Create a group box for environmental information
        environmental_group_box = QGroupBox("Environmental Information")
        environmental_group_box.setLayout(self.environmental_layout)

        # Create a layout for location and environmental information
        loc_env_layout = QVBoxLayout()
        loc_env_layout.addWidget(location_group_box)
        loc_env_layout.addWidget(environmental_group_box)

        # Create a widget to hold the loc_env_layout
        loc_env_widget = QWidget()
        loc_env_widget.setLayout(loc_env_layout)

        # Create a scroll area for the loc_env_widget
        loc_env_scroll_area = QScrollArea()
        loc_env_scroll_area.setWidgetResizable(True)
        loc_env_scroll_area.setWidget(loc_env_widget)

        # Create a layout for the main content (image and loc_env_scroll_area)
        main_content_layout = QVBoxLayout()
        main_content_layout.addWidget(image_widget)
        main_content_layout.addWidget(loc_env_scroll_area)

        # Create a widget to hold the main content layout
        main_content_widget = QWidget()
        main_content_widget.setLayout(main_content_layout)

        # Create a layout for the technical information accordion
        self.technical_layout = QVBoxLayout()

        # Create a group box for the technical information accordion
        technical_group_box = QGroupBox("Technical Information")
        technical_group_box.setLayout(self.technical_layout)

        # Create a scroll area for the technical information
        technical_scroll_area = QScrollArea()
        technical_scroll_area.setWidgetResizable(True)
        technical_scroll_area.setWidget(technical_group_box)

        # Create a main layout to include main_content_widget and technical_scroll_area
        main_layout = QHBoxLayout()
        main_layout.addWidget(main_content_widget, 3)
        main_layout.addWidget(technical_scroll_area, 1)

        # Create a central widget to set the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        # Create a layout for the additional information
        self.additional_layout = QHBoxLayout()

        # Create a group box for additional information
        additional_group_box = QGroupBox("Additional Information")
        additional_group_box.setLayout(self.additional_layout)

        # Create a final layout to include everything
        final_layout = QVBoxLayout()
        final_layout.addWidget(central_widget)
        final_layout.addWidget(additional_group_box)

        final_widget = QWidget()
        final_widget.setLayout(final_layout)
        self.setCentralWidget(final_widget)

    def open_image(self):
        # Open a file dialog to choose an image file
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.pol);;All Files (*)",
        )

        # Check if a file was selected
        if file_path:
            ext = pathlib.Path(file_path).suffix
            if ext == ".pol":
                self.polarImage = PolarImage(file_path)
                self.data_dict = self.polarImage.header
                png_path = str(self.polarImage.saveto("temp/temp.png"))
                self.pixmap = QPixmap(png_path)
            elif ext == ".png":
                with Image.open(file_path) as img:
                    self.pixmap = QPixmap(file_path)
                    self.data_dict = json.loads(img.text["json_data"])
            else:
                self.pixmap = QPixmap(file_path)

            # Resize the image to fit the window height while maintaining the aspect ratio
            pixmap = self.scale_image_to_window(self.pixmap)

            # Set the pixmap to the QLabel
            self.image_label.setPixmap(pixmap)

            # Clear existing key-value pairs
            self.clear_key_value_pairs()

            # Add new key-value pairs
            self.add_key_value_pairs(self.data_dict)

    def scale_image_to_window(self, pixmap):
        # Get the current window height
        height = self.centralWidget().height()
        width = self.centralWidget().width()
        # Scale the image to fit the window height while maintaining the aspect ratio
        return pixmap.scaled(
            width//2, height//2, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

    def customResizeEvent(self, event):
        # Resize the image when the window size changes
        if self.polarImage:
            pixmap = self.image_label.pixmap()
            if self.pixmap:
                pixmap = self.scale_image_to_window(self.pixmap)
                self.image_label.setPixmap(pixmap)

        # Call the base class implementation
        super().resizeEvent(event)

    def add_key_value_pairs(self, data_dict):
        location_keys = ["LAT", "LONG"]
        general_keys = [
            "OWNER",
            "VINFO",
            "VERSN",
            "TOWER",
            "IDENT",
            "USER",
            "DATE",
            "TIME",
            "ZONE",
        ]
        technical_keys = [
            "TMINT",
            "NMEAN",
            "ANALM",
            "AMINT",
            "NIPOL",
            "NUMRE",
            "RPT",
            "SDRNG",
            "SFREQ",
            "FIFO",
            "BO2RA",
            "HDGDL",
            "GYROC",
            "GYROV",
            "VGAIN",
            "CMPOFF",
        ]
        environmental_keys = [
            "WDEPF",
            "P_DEP",
            "PDEPV",
            "SHIPR",
            "SHIRV",
            "SHIPS",
            "SHISV",
            "SPTWL",
            "SPWLV",
            "SPTWT",
            "SPWTV",
            "WINDS",
            "WINSV",
            "WINDR",
            "WINRV",
            "WINDT",
            "WINDH",
            "WATSP",
            "WATSV",
        ]
        additional_keys = ["DABIT", "F0001", "RPM", "EOH"]

        # Add general information
        general_info_text = ""
        for key in general_keys:
            if key in data_dict:
                value = data_dict[key]
                general_info_text += f"<b>{key}:</b> {value['value']}   "
        self.general_info_label.setText(general_info_text)

        # Add location information
        row, col = 0, 0
        for key in location_keys:
            if key in data_dict:
                value = data_dict[key]
                key_label = QLabel(key)
                value_textbox = QLineEdit(str(value["value"]))
                value_textbox.setReadOnly(True)
                value_textbox.setToolTip(value["description"])
                self.location_layout.addWidget(key_label, row, col * 2)
                self.location_layout.addWidget(value_textbox, row, col * 2 + 1)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

        # Add technical information
        for key in technical_keys:
            if key in data_dict:
                value = data_dict[key]
                key_label = QLabel(key)
                value_textbox = QLineEdit(str(value["value"]))
                value_textbox.setReadOnly(True)
                value_textbox.setToolTip(value["description"])
                technical_group = QGroupBox(key)
                technical_layout = QVBoxLayout()
                technical_layout.addWidget(value_textbox)
                technical_group.setLayout(technical_layout)
                self.technical_layout.addWidget(technical_group)

        # Add environmental information
        row, col = 0, 0
        for key in environmental_keys:
            if key in data_dict:
                value = data_dict[key]
                key_label = QLabel(key)
                value_textbox = QLineEdit(str(value["value"]))
                value_textbox.setReadOnly(True)
                value_textbox.setToolTip(value["description"])
                self.environmental_layout.addWidget(key_label, row, col * 2)
                self.environmental_layout.addWidget(value_textbox, row, col * 2 + 1)
                col += 1
                if col >= 5:
                    col = 0
                    row += 1

        # Add additional information
        for key in additional_keys:
            if key in data_dict:
                value = data_dict[key]
                key_label = QLabel(key)
                value_textbox = QLineEdit(str(value["value"]))
                value_textbox.setReadOnly(True)
                value_textbox.setToolTip(value["description"])
                self.additional_layout.addWidget(key_label)
                self.additional_layout.addWidget(value_textbox)

    def clear_key_value_pairs(self):
        # Clear existing key-value pairs from the layouts
        for layout in [
            self.location_layout,
            self.technical_layout,
            self.environmental_layout,
            self.additional_layout,
        ]:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def save_image(self):
        # Opens a dialog for saving a file
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "",
            "Image files (*.png);;All Files (*)",
            options=options,
        )
        if fileName:
            self.polarImage.save_with_metadata(output_path=fileName)
            print(f"Saved content to {fileName}")


def main():
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    qdarktheme.setup_theme("auto")
    window = PolarImageInspector()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
