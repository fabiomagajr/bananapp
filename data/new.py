import sys
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QLabel

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem
)
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

class EditableTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cellChanged.connect(self.cell_edited)

    def cell_edited(self, row, column):
        if self.parent().df is not None:
            new_value = self.item(row, column).text()
            self.parent().df.iat[row, column] = new_value
            self.parent().save_file()

class FileScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Scanner App")
        self.setGeometry(100, 100, 800, 600)

        self.df = None
        self.file_path = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.choose_file_button = QPushButton("Choose File")
        self.choose_file_button.clicked.connect(self.choose_file)
        self.layout.addWidget(self.choose_file_button)

        self.filter_label = QLabel("Filter:")
        self.layout.addWidget(self.filter_label)

        self.filter_field = QLineEdit()
        self.filter_field.textChanged.connect(self.apply_filter)
        self.layout.addWidget(self.filter_field)

        self.table_widget = EditableTableWidget(self)
        self.layout.addWidget(self.table_widget)

    def save_file(self):
        try:
            if self.file_path.endswith(".csv"):
                self.df.to_csv(self.file_path, index=False)
            elif self.file_path.endswith((".xls", ".xlsx")):
                self.df.to_excel(self.file_path, index=False)
            elif self.file_path.endswith(".json"):
                self.df.to_json(self.file_path, orient="records", lines=False)
            elif self.file_path.endswith(".xml"):
                self.df.to_xml(self.file_path, index=False)
        except Exception as e:
            print(f"Error saving file: {e}")

    def apply_filter(self):
        if self.df is not None:
            filter_text = self.filter_field.text().lower()
            filtered_df = self.df[self.df.apply(
                lambda row: row.astype(str).str.contains(filter_text, case=False).any(), axis=1
            )]
            self.populate_table(filtered_df)

    def populate_table(self, df=None):
        if df is None:
            df = self.df
        if df is not None:
            self.table_widget.blockSignals(True)
            self.table_widget.setRowCount(df.shape[0])
            self.table_widget.setColumnCount(df.shape[1])
            self.table_widget.setHorizontalHeaderLabels(df.columns)

            for row in range(df.shape[0]):
                for col in range(df.shape[1]):
                    value = str(df.iat[row, col])
                    self.table_widget.setItem(row, col, QTableWidgetItem(value))

            self.table_widget.resizeColumnsToContents()
            self.table_widget.blockSignals(False)

class FileScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Scanner App")
        self.setGeometry(100, 100, 800, 600)

        self.df = None  # DataFrame to hold the file data

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Button to choose file
        self.choose_file_button = QPushButton("Choose File")
        self.choose_file_button.clicked.connect(self.choose_file)
        self.layout.addWidget(self.choose_file_button)

        # Table widget to display data
        self.table_widget = QTableWidget()
        self.layout.addWidget(self.table_widget)

    def choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Data Files (*.csv *.xls *.xlsx *.json *.xml)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        try:
            # Load file into a pandas DataFrame
            if file_path.endswith(".csv"):
                self.df = pd.read_csv(file_path)
            elif file_path.endswith((".xls", ".xlsx")):
                self.df = pd.read_excel(file_path)
            elif file_path.endswith(".json"):
                self.df = pd.read_json(file_path)
            elif file_path.endswith(".xml"):
                self.df = pd.read_xml(file_path)
            else:
                raise ValueError("Unsupported file format")

            # Populate the table widget with the DataFrame
            self.populate_table()
        except Exception as e:
            print(f"Error loading file: {e}")

    def populate_table(self):
        if self.df is not None:
            self.table_widget.setRowCount(self.df.shape[0])
            self.table_widget.setColumnCount(self.df.shape[1])
            self.table_widget.setHorizontalHeaderLabels(self.df.columns)

            for row in range(self.df.shape[0]):
                for col in range(self.df.shape[1]):
                    value = str(self.df.iat[row, col])
                    self.table_widget.setItem(row, col, QTableWidgetItem(value))

            self.table_widget.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileScannerApp()
    window.show()
    sys.exit(app.exec())