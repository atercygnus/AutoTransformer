from PyQt5 import QtWidgets
from datetime import datetime


class Logger(QtWidgets.QTextBrowser):
    def __init__(self, *args):
        super().__init__(*args)
        self.messages=[]
    prefix = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
    "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
    "p, li { white-space: pre-wrap; }\n"
    "</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
    suffix = "</body></html>"
    def log(self, text):
        try:
            now = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            print('<b>' + now + '</b> ' + str(text))
            self.messages.append('<b>' + now + '</b> ' + text)
            self.setHtml(self.prefix+'<br>'.join(self.messages[::-1])+self.suffix)
        except BaseException as e:
            print(e)