import sys
import os
import pandas as pd
import json
import yaml
import sqlite3
import xml.etree.ElementTree as ET
import io
import resources_rc
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableView, QVBoxLayout, 
                                QHBoxLayout, QWidget, QPushButton, QFileDialog, 
                                QLineEdit, QLabel, QMessageBox, QHeaderView, QComboBox,
                                QStatusBar,QProgressBar, )
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel, Signal
from PySide6.QtGui import QAction, QIcon, QColor, QPalette, QFont
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel, Signal, QTimer
try:
    import bson
    BSON_AVAILABLE = True
except ImportError:
    BSON_AVAILABLE = False
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
class PandasModel(QAbstractTableModel):
    dataChanged = Signal(QModelIndex, QModelIndex)
    
    def __init__(self, data):
        super().__init__()
        self._data = data
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._data.index)
        
    def columnCount(self, parent=QModelIndex()):
        return len(self._data.columns)
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
            
        if role == Qt.BackgroundRole:
            return QColor(45, 45, 45)
            
        if role == Qt.ForegroundRole:
            return QColor(200, 200, 200)
            
        return None
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(self._data.index[section])
        return None
        
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
            
        row = index.row()
        col = index.column()
        column_name = self._data.columns[col]
        
        try:
            # Try to convert to original dtype if possible
            orig_dtype = self._data[column_name].dtype
            converted_value = pd.Series([value], dtype=orig_dtype)[0]
            self._data.iloc[row, col] = converted_value
        except:
            # If conversion fails, use string value
            self._data.iloc[row, col] = value
            
        self.dataChanged.emit(index, index)
        return True
        
    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        
    def get_dataframe(self):
        return self._data

class EditorUniversal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_file_type = None
        self.df = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Editor Universal - Versão Banana 1.0")
        self.setMinimumSize(800, 600)
        self.setup_dark_theme()
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Toolbar layout
        self.toolbar_layout = QHBoxLayout()
        
        # Create buttons
        self.btn_open = QPushButton(QIcon.fromTheme("document-open", QIcon(":/icons/open.png")), "Abrir")
        self.btn_open.clicked.connect(self.open_file)

        # combobox for file type selection
        self.file_type_label = QLabel("Perfil de Saída:")
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["CSV", "Excel", "SQLite", "JSON", "XML", "YAML"])
        
        self.btn_save = QPushButton(QIcon.fromTheme("document-save", QIcon(":/icons/save.png")), "Salvar")
        self.btn_save.clicked.connect(self.save_file)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Inicialmente invisível
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m linhas carregadas (%p%)")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #5c5c5c;
                border-radius: 3px;
                text-align: center;
                background-color: #353535;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        
        
        # Filter layout
        self.filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Filtrar:")
        self.filter_input = QLineEdit()
        self.filter_input.textChanged.connect(self.filter_table)
        self.filter_input.setClearButtonEnabled(True)
        
        # Add widgets to layouts
        self.toolbar_layout.addWidget(self.btn_open)
        self.toolbar_layout.addStretch()  # Isso cria um espaço flexível empurrando os próximos widgets para a direita
        self.toolbar_layout.addWidget(QLabel("Perfil de Saída:"))
        self.toolbar_layout.addWidget(self.file_type_combo)
        self.toolbar_layout.addWidget(self.btn_save)
        
        self.filter_layout.addWidget(self.filter_label)
        self.filter_layout.addWidget(self.filter_input)
        
        # Create table view
        self.table_view = QTableView()
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setAlternatingRowColors(True)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add layouts to main layout
        self.main_layout.addLayout(self.toolbar_layout)
        # Adicionar a barra de progresso ao layout principal
        self.main_layout.addWidget(self.progress_bar)

        # Adicionar o layout de filtro depois da barra de progresso
        self.main_layout.addLayout(self.filter_layout)
        
        self.main_layout.addWidget(self.table_view)
        
        # Setup menu
        self.setup_menu()
        
        # Status bar initial message
        self.status_bar.showMessage("Pronto. Abra um arquivo para começar!")
        
    def setup_dark_theme(self):
        app = QApplication.instance()
        
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 255, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        
        app.setPalette(dark_palette)
        app.setStyleSheet("""
            QToolTip { 
                color: #ffffff; 
                background-color: #2a82da; 
                border: 1px solid white; 
            }
            QTableView {
                gridline-color: #454545;
                color: #E0E0E0;
                background-color: #292929;
                selection-background-color: #2a82da;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 4px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #2a82da;
            }
            QLineEdit {
                border: 1px solid #5c5c5c;
                border-radius: 3px;
                padding: 3px;
                background-color: #353535;
                color: #ffffff;
            }
            QComboBox {
                border: 1px solid #5c5c5c;
                border-radius: 3px;
                padding: 3px 18px 3px 3px;
                min-width: 6em;
                background-color: #353535;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #2a2a2a;
                color: #E0E0E0;
            }
        """)
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&Arquivo')
        
        open_action = QAction(QIcon.fromTheme("document-open", QIcon(":/icons/open.png")), '&Abrir', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save", QIcon(":/icons/save.png")), '&Salvar', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(QIcon.fromTheme("application-exit", QIcon(":/icons/exit.png")), '&Sair', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('&Ajuda')
        
        about_action = QAction(QIcon.fromTheme("help-about", QIcon(":/icons/about.png")), '&Sobre', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def show_about(self):
        QMessageBox.about(self, "Sobre - Editor Universal",
                            "<h3>Editor Universal - Versão Banana 1.0</h3>"
                            "<p>Um editor universal para arquivos de dados.</p>"
                            "<p>Suporta CSV, Excel, SQLite, JSON, XML, YAML e BSON.</p>"
                            "<p><b>🍌 Versão Banana 1.0 🍌</b></p>")
        
    def open_file(self):
        options = QFileDialog.Options()
        file_types = "Todos os arquivos (*);;CSV (*.csv);;Excel (*.xls *.xlsx);;SQLite (*.db *.sqlite);;JSON (*.json);;XML (*.xml);;YAML (*.yml *.yaml)"
        if BSON_AVAILABLE:
            file_types += ";;BSON (*.bson)"
            
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo", "", file_types, options=options)
        
        if file_name:
            try:
                # Exibir a barra de progresso
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.progress_bar.setMaximum(100)  # Padrão para porcentagem
                self.status_bar.showMessage("Carregando arquivo...")
                
                # Processar o arquivo e atualizar a barra de progresso
                QApplication.processEvents()  # Importante para atualizar a interface
                
                # Determinar file type from extension
                extension = os.path.splitext(file_name)[1].lower()
                
                # Para formatos em que podemos contar linhas facilmente
                if extension in ['.csv']:
                    try:
                        # Contar linhas para arquivos CSV
                        with open(file_name, 'r', encoding='utf-8') as f:
                            total_lines = sum(1 for _ in f)
                        self.progress_bar.setMaximum(total_lines)
                        
                        # Atualiza para 25% após contar as linhas
                        self.progress_bar.setValue(total_lines // 4)
                        QApplication.processEvents()
                        
                        # Abrir o arquivo novamente para processamento
                        self.file_type_combo.setCurrentText("CSV")
                        self.df = pd.read_csv(file_name)
                        
                        # Atualiza para 100% após carregar
                        self.progress_bar.setValue(total_lines)
                    except Exception:
                        # Se falhar ao contar linhas, use abordagem padrão
                        self.progress_bar.setValue(50)
                        QApplication.processEvents()
                        self.df = pd.read_csv(file_name)
                        self.progress_bar.setValue(100)
                
                elif extension in ['.xls', '.xlsx']:
                    self.file_type_combo.setCurrentText("Excel")
                    # Para Excel, usamos uma abordagem de etapas
                    self.progress_bar.setValue(30)  # Início do carregamento
                    QApplication.processEvents()
                    
                    self.df = pd.read_excel(file_name)
                    self.progress_bar.setValue(100)  # Carregamento completo
                    QApplication.processEvents()
                    
                elif extension in ['.db', '.sqlite']:
                    self.file_type_combo.setCurrentText("SQLite")
                    
                    # Etapa 1: Conectar ao banco
                    self.progress_bar.setValue(20)
                    QApplication.processEvents()
                    
                    conn = sqlite3.connect(file_name)
                    cursor = conn.cursor()
                    
                    # Etapa 2: Buscar tabelas
                    self.progress_bar.setValue(40)
                    QApplication.processEvents()
                    
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    
                    if len(tables) == 0:
                        conn.close()
                        self.progress_bar.setVisible(False)
                        QMessageBox.warning(self, "Erro", "O arquivo SQLite não contém tabelas.")
                        return
                    
                    # Seleciona a primeira tabela
                    table_name = tables[0][0]
                    
                    # Etapa 3: Carregar dados
                    self.progress_bar.setValue(60)
                    QApplication.processEvents()
                    
                    self.df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    conn.close()
                    
                    # Etapa 4: Finaliza
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                    
                elif extension in ['.json']:
                    self.file_type_combo.setCurrentText("JSON")
                    
                    # Etapa 1: Início
                    self.progress_bar.setValue(25)
                    QApplication.processEvents()
                    
                    # Etapa 2: Leitura do arquivo
                    with open(file_name, 'r', encoding='utf-8') as f:
                        self.progress_bar.setValue(50)
                        QApplication.processEvents()
                        json_data = json.load(f)
                    
                    # Etapa 3: Conversão para DataFrame
                    self.progress_bar.setValue(75)
                    QApplication.processEvents()
                    
                    # Handle both list of objects and single object
                    if isinstance(json_data, list):
                        self.df = pd.json_normalize(json_data)
                    else:
                        self.df = pd.json_normalize([json_data])
                    
                    # Etapa 4: Finaliza
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                    
                elif extension in ['.xml']:
                    self.file_type_combo.setCurrentText("XML")
                    
                    # Etapa 1: Início
                    self.progress_bar.setValue(25)
                    QApplication.processEvents()
                    
                    # Etapa 2: Parse do XML
                    tree = ET.parse(file_name)
                    root = tree.getroot()
                    
                    self.progress_bar.setValue(50)
                    QApplication.processEvents()
                    
                    # Etapa 3: Conversão para DataFrame
                    data = []
                    for child in root:
                        row = {}
                        for element in child:
                            row[element.tag] = element.text
                        data.append(row)
                        
                        # Atualiza periodicamente para arquivos grandes
                        if len(data) % 100 == 0:
                            self.progress_bar.setValue(50 + min(len(data) // 10, 40))
                            QApplication.processEvents()
                    
                    self.df = pd.DataFrame(data)
                    
                    # Etapa 4: Finaliza
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                    
                elif extension in ['.yml', '.yaml']:
                    self.file_type_combo.setCurrentText("YAML")
                    
                    # Etapa 1: Início
                    self.progress_bar.setValue(30)
                    QApplication.processEvents()
                    
                    # Etapa 2: Leitura do arquivo
                    with open(file_name, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)
                    
                    self.progress_bar.setValue(70)
                    QApplication.processEvents()
                    
                    # Etapa 3: Conversão para DataFrame
                    if isinstance(yaml_data, list):
                        self.df = pd.DataFrame(yaml_data)
                    else:
                        self.df = pd.DataFrame([yaml_data])
                    
                    # Etapa 4: Finaliza
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                    
                elif extension in ['.bson'] and BSON_AVAILABLE:
                    self.file_type_combo.setCurrentText("BSON")
                    
                    # Etapa 1: Início
                    self.progress_bar.setValue(30)
                    QApplication.processEvents()
                    
                    # Etapa 2: Leitura do arquivo
                    with open(file_name, 'rb') as f:
                        bson_data = bson.loads(f.read())
                    
                    self.progress_bar.setValue(70)
                    QApplication.processEvents()
                    
                    # Etapa 3: Conversão para DataFrame
                    self.df = pd.DataFrame([bson_data])
                    
                    # Etapa 4: Finaliza
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                    
                else:
                    # Tenta inferir o formato
                    self.progress_bar.setValue(30)
                    QApplication.processEvents()
                    
                    try:
                        self.df = pd.read_csv(file_name)
                        self.file_type_combo.setCurrentText("CSV")
                    except:
                        self.progress_bar.setVisible(False)
                        QMessageBox.warning(self, "Erro", "Formato de arquivo não reconhecido ou não suportado.")
                        return
                    
                    self.progress_bar.setValue(100)
                    QApplication.processEvents()
                
                # Após o carregamento completo, exibir os dados
                self.current_file = file_name
                self.current_file_type = self.file_type_combo.currentText()
                self.display_data()
                
                # Atualizar status e esconder a barra após um curto delay
                self.status_bar.showMessage(f"Arquivo carregado: {os.path.basename(file_name)} ({len(self.df)} linhas)")
                QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
                
            except Exception as e:
                self.progress_bar.setVisible(False)
                QMessageBox.critical(self, "Erro ao abrir arquivo", f"Erro: {str(e)}")
        
    def display_data(self):
        if self.df is not None:
            # Create model and proxy model for filtering
            self.model = PandasModel(self.df)
            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy_model.setSourceModel(self.model)
            
            # Set the proxy model to the table view
            self.table_view.setModel(self.proxy_model)
            
            # Enable sorting
            self.table_view.setSortingEnabled(True)

            self.table_view.setModel(self.proxy_model)
            self.table_view.setSortingEnabled(True)
            
            # Ajuste automático das colunas baseado no conteúdo
            self.table_view.resizeColumnsToContents()
            
            # Ajuste adicional para garantir que os cabeçalhos também sejam considerados
            header = self.table_view.horizontalHeader()
            for column in range(len(self.df.columns)):
                width = header.sectionSize(column)
                # Aumentamos um pouco a largura para melhor visualização
                header.resizeSection(column, width + 20)
            
            # Update window title
            if self.current_file:
                self.setWindowTitle(f"Editor Universal - Versão Banana 1.0 - {os.path.basename(self.current_file)}")
            
            
    def filter_table(self, text):
        self.proxy_model.setFilterFixedString(text)
        self.proxy_model.setFilterKeyColumn(-1)  # -1 means search all columns
        
    def save_file(self):
        if self.df is None:
            QMessageBox.warning(self, "Aviso", "Nenhum dado para salvar.")
            return
            
        # Update dataframe from model to ensure all edits are saved
        self.df = self.model.get_dataframe()
        
        options = QFileDialog.Options()
        file_type = self.file_type_combo.currentText()
        
        if file_type == "CSV":
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "CSV (*.csv)", options=options)
            if file_name:
                if not file_name.endswith('.csv'):
                    file_name += '.csv'
                self.df.to_csv(file_name, index=False)
                
        elif file_type == "Excel":
            if not EXCEL_AVAILABLE:
                QMessageBox.warning(self, "Aviso", "Para salvar em formato Excel (.xlsx), você precisa instalar a biblioteca 'openpyxl'.\nUse o comando: pip install openpyxl")
                return
                
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "Excel (*.xlsx)", options=options)
            if file_name:
                if not file_name.endswith('.xlsx'):
                    file_name += '.xlsx'
                self.df.to_excel(file_name, index=False)
                
        elif file_type == "SQLite":
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "SQLite (*.db)", options=options)
            if file_name:
                if not file_name.endswith('.db'):
                    file_name += '.db'
                conn = sqlite3.connect(file_name)
                self.df.to_sql('data', conn, if_exists='replace', index=False)
                conn.close()
                
        elif file_type == "JSON":
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "JSON (*.json)", options=options)
            if file_name:
                if not file_name.endswith('.json'):
                    file_name += '.json'
                self.df.to_json(file_name, orient='records', lines=False)
                
        elif file_type == "XML":
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "XML (*.xml)", options=options)
            if file_name:
                if not file_name.endswith('.xml'):
                    file_name += '.xml'
                    
                # Convert DataFrame to XML
                root = ET.Element('root')
                for _, row in self.df.iterrows():
                    record = ET.SubElement(root, 'record')
                    for col_name, value in row.items():
                        child = ET.SubElement(record, str(col_name))
                        child.text = str(value)
                
                tree = ET.ElementTree(root)
                tree.write(file_name, encoding='utf-8', xml_declaration=True)
                
        elif file_type == "YAML":
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "YAML (*.yaml)", options=options)
            if file_name:
                if not file_name.endswith('.yaml') and not file_name.endswith('.yml'):
                    file_name += '.yaml'
                    
                with open(file_name, 'w', encoding='utf-8') as f:
                    yaml.dump(self.df.to_dict('records'), f)
                    
        elif file_type == "BSON" and BSON_AVAILABLE:
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "BSON (*.bson)", options=options)
            if file_name:
                if not file_name.endswith('.bson'):
                    file_name += '.bson'
                    
                with open(file_name, 'wb') as f:
                    f.write(bson.dumps(self.df.to_dict('records')))
                    
        else:
            QMessageBox.warning(self, "Aviso", f"Formato {file_type} não suportado para salvar.")
            return
            
        if file_name:
            self.current_file = file_name
            self.current_file_type = file_type
            self.status_bar.showMessage(f"Arquivo salvo: {os.path.basename(file_name)}")
            self.setWindowTitle(f"Editor Universal - Versão Banana 1.0 - {os.path.basename(file_name)}")

def main():
    app = QApplication(sys.argv)
    # Para Windows - ID da aplicação para agrupar na barra de tarefas
    if sys.platform == "win32":
        import ctypes
        app_id = 'banana.editoruniversal.1.0'  # Um identificador único para sua aplicação
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    # Carregar ícone personalizado (substitua pelo caminho real)
    icon_path = "icons/banana.png"  
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # Aplicar o mesmo ícone à janela principal
    editor = EditorUniversal()
    editor.setWindowIcon(app_icon)
    
    # Setup icon resources (if we had actual icon files)
    # QDir.addSearchPath("icons", ":/icons")
    
    # Set font to improve readability in dark theme
    font = QFont("Arial", 10)
    app.setFont(font)
    
    editor = EditorUniversal()
    editor.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()