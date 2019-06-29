#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Author: _defined
@Time:  2019/6/10 11:53
@Description: 
"""
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, QTimer
import sys
import MainWindow
import os
import string
import re
import pandas as pd
import json

DEFAULT_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: lightblue;
    width: 10px;
    margin: 1px;
}
"""


class Thread(QThread):
    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        pass


class Main(QMainWindow, MainWindow.Ui_MainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.captchaAns = {}
        self.user_dict = string.ascii_letters + string.digits  # 用户自定义字典，默认是所有字母数字
        self.files = []
        self.filenames = []
        self.folderPath = ""
        self.progressMax = self.progressNow = self.progressLast = 0
        self.timesMax = self.timesNow = 1
        self.hasError = False
        self.record_name = 'record.json'
        self.record = False
        self.csv_name = 'validate.csv'
        self.csv = False
        self.val_df = None
        self.repeat = False
        self.defaultPath = r'E:\\'
        self.extension = ['png', 'jpg', 'jpeg', 'bmp', 'svg', 'ico']
        self.progressBar.setStyleSheet(DEFAULT_STYLE)
        self.lineEditInput.setVisible(False)
        self.progressBar.setVisible(False)
        self.pushButtonSave.setVisible(False)
        self.checkBox.setVisible(False)
        self.checkBox_2.setVisible(False)
        self.pushButtonStart.setVisible(False)
        self.label_2.setVisible(False)
        self.pushButtonBack.setVisible(False)

        self.start_timer = QTimer()
        self.start_timer.timeout.connect(self.startLabel)
        self.back_timer = QTimer()
        self.back_timer.timeout.connect(self.backPic)

        self.lineEditInput.returnPressed.connect(self.nextPic)
        self.pushButtonStart.clicked.connect(lambda: self.start_timer.start(100))
        self.pushButtonOpen.clicked.connect(self.openFile)
        self.pushButtonSave.clicked.connect(self.saveTemp)
        self.pushButtonBack.clicked.connect(lambda: self.back_timer.start(100))

        if os.path.exists('user_dict.txt'):  # 如果有用户自定义的字典，则以用户字典为准
            with open('user_dict.txt', 'r+', encoding='utf-8') as reader:
                content = reader.read()
                content = re.sub('\n|\r|\t|\s*', '', content)  # 去除一些回车换行等字符
                self.user_dict = content

    def openFile(self):
        # dialog = QFileDialog(self, '選取文件夾', '/Users/david/file/jupyter/simple-railway-captcha-solver/data/')
        # dialog.setFileMode(QFileDialog.DirectoryOnly)
        # dialog.setNameFilter('Images (*.png *.jpeg *.jpg)')
        # if dialog.exec_() == QDialog.Accepted:
        #     self.files = dialog.selectedFiles()
        #     print(self.files)

        self.folderPath = QFileDialog.getExistingDirectory(self, '选取文件夹', self.defaultPath)
        print('所选取文件夹目录为：', self.folderPath)

        if self.folderPath:
            for root, dirs, files in os.walk(self.folderPath):
                # 检查是否有record.json
                if self.record_name in files:
                    recordPath = os.path.join(self.folderPath, self.record_name)
                    with open(recordPath, 'r+') as f:
                        load_record = json.load(f)
                        self.progressLast = int(load_record['last_label_index'])
                    self.record = True

                # 检查是否有validate.csv
                if self.csv_name in files:
                    csvPath = os.path.join(self.folderPath, self.csv_name)  # self.folderPath + '/' + self.csv_name
                    self.val_df = pd.read_csv(csvPath, dtype={'index': str})
                    # print(self.val_df,self.val_df.set_index('index')['label'].to_dict())
                    self.csv = True

                # 去掉不是图片的文件
                files = [f for f in files for ext in self.extension if '.' + ext in f]

                # 存在csv且长度与图片数量长度一致，可以选择重复验证
                if self.csv and len(self.val_df) == len(files):
                    self.checkBox_2.setVisible(True)
                    self.checkBox_2.setEnabled(True)

                # 存在record且标记index与csv长度一致，可选择继续标记
                elif self.record and self.csv and len(self.val_df) == self.progressLast:
                    self.checkBox.setVisible(True)
                    self.checkBox.setEnabled(True)
                    self.checkBox.setText("上次标记到第" + str(self.progressLast + 1) + "张，是否继续")

                # noinspection PyBroadException
                try:
                    files.sort(key=lambda x: int(x.split('.')[0]))  # 按数字进行排序
                except:
                    files.sort()

                for file in files:
                    filepath = os.path.join(root, file)
                    self.files.append(filepath)
                    filename = file.split('.')[0]
                    self.filenames.append(filename)

            if len(self.files) > 0:
                self.lineEditFile.setText(self.folderPath)
                self.pushButtonStart.setVisible(True)
                self.pushButtonStart.setEnabled(True)
            else:
                QMessageBox.information(self, "提示", "文件夹中没有图片")
                self.pushButtonStart.setEnabled(False)

    def startLabel(self):
        if self.checkBox.isChecked():  # 继续标注
            self.captchaAns = self.val_df.set_index('index')['label'].to_dict()
            self.progressNow = self.progressLast
        elif self.checkBox_2.isChecked():  # 重复验证
            self.captchaAns = self.val_df.set_index('index')['label'].to_dict()
            self.repeat = True
            self.progressNow = 0
        else:  # 新的标注
            self.progressNow = 0

        self.progressMax = len(self.files)
        image = QImage(self.files[self.progressNow])
        self.labelPic.setPixmap(QPixmap.fromImage(image))
        self.setProgressLabel()
        self.progressBar.setMaximum(self.progressMax * self.timesMax)
        self.progressBar.setValue(self.progressNow)
        self.pushButtonOpen.setEnabled(False)
        self.pushButtonStart.setEnabled(False)
        self.checkBox.setEnabled(False)
        self.checkBox_2.setEnabled(False)
        self.lineEditInput.setVisible(True)
        self.lineEditInput.setEnabled(True)
        self.lineEditInput.setFocus()
        self.progressBar.setVisible(True)
        self.pushButtonSave.setVisible(True)
        self.pushButtonSave.setEnabled(True)
        self.pushButtonBack.setVisible(True)
        self.label_2.setVisible(True)
        self.setTimesLabel()
        self.start_timer.stop()

    def nextPic(self):
        check = True
        text = self.lineEditInput.text()
        # print('text', type(text))
        for c in text:  # 检查输入的字符是否是英文字符
            if c not in self.user_dict:
                check = False
                break

        if check:
            if 4 <= len(text):
                # text = text.lower()
                print('self.checkAns(text)', self.checkAns(text))
                if self.checkAns(text):
                    self.switch2NextPic()
                    self.progressBar.setValue(self.progressBar.value() + 1)
                else:
                    s = "你输入的跟前一次{}不同，请检查后再送出确认的答案，答案将以" \
                        "这次送出的为主。".format(self.captchaAns[self.filenames[self.progressNow]])
                    QMessageBox.information(self, "提示", s)
            else:
                QMessageBox.information(self, "提示", "验证码至少为4位")
        else:
            QMessageBox.information(self, "提示", "请输入数字字母，或自定义user_dict.txt文件并填入验证码可能包含的字符")

    def checkAns(self, text):
        if not self.repeat:
            self.captchaAns[self.filenames[self.progressNow]] = text
            return True
        else:
            if text == self.captchaAns[self.filenames[self.progressNow]]:
                print()
                return True
            elif self.hasError:
                self.hasError = False
                self.captchaAns[self.filenames[self.progressNow]] = text
                return True
            else:
                self.hasError = True
                return False

    def setProgressLabel(self):
        s = '共' + str(self.progressMax) + '张，目前正处理到第' + str(self.progressNow + 1) + '张'
        self.labelProgress.setText(s)

    def setTimesLabel(self):
        s = '共要标记' + str(self.timesMax) + '次，目前正标记到第' + str(self.timesNow) + '次'
        self.labelTimes.setText(s)

    def backPic(self):
        if self.progressNow > 0:
            self.progressNow -= 2
            self.progressBar.setValue(self.progressNow + 1)
            self.back_timer.stop()
            self.switch2NextPic()
        else:
            QMessageBox.information(self, '提示', '无法在第一张往前...')
            self.back_timer.stop()

    def switch2NextPic(self):
        self.hasError = False
        if self.progressNow == self.progressMax - 1:
            try:
                if os.path.exists(os.path.join(self.folderPath, self.record_name)):
                    os.remove(os.path.join(self.folderPath, self.record_name))
            except Exception as e:
                print(e)
            self.save2csv()
            # if self.timesNow == self.timesMax:
            #     self.save2csv()
            # else:
            #     self.switch2NextTimes()
        else:
            self.progressNow += 1
            self.setProgressLabel()
            image = QImage(self.files[self.progressNow])
            self.labelPic.setPixmap(QPixmap.fromImage(image))
            self.lineEditInput.setText("")
            self.lineEditInput.setFocus()

    # def switch2NextTimes(self):
    #     self.timesNow += 1
    #     self.progressNow = 0
    #     image = QImage(self.files[self.progressNow])
    #     self.labelPic.setPixmap(QPixmap.fromImage(image))
    #     self.setTimesLabel()
    #     self.setProgressLabel()
    #     self.lineEditInput.setText("")
    #     self.lineEditInput.setFocus()

    def saveTemp(self):
        s = "还沒有完成，确定要暂时保存吗？"
        reply = QMessageBox.information(self, '提示', s, QMessageBox.Ok | QMessageBox.Close,
                                        QMessageBox.Close)
        if reply == QMessageBox.Ok:
            saveRecordPath = os.path.join(self.folderPath, self.record_name)  # self.folderPath + '/' + self.record_name
            record_dict = {'last_label_index': self.progressNow}
            with open(saveRecordPath, 'w') as f:
                json.dump(record_dict, f)
            self.save2csv()

    def save2csv(self):
        saveFilePath = os.path.join(self.folderPath, self.csv_name)  # self.folderPath + '/' + self.csv_name
        saveFile = QFileDialog.getSaveFileName(
            self, "保存", saveFilePath, 'CSV files (*.csv)')
        print(saveFile[0])
        if saveFile[0]:
            print('captchaAns', self.captchaAns)
            index = list(map(str, self.captchaAns.keys()))
            index.sort()
            print('captchaAns keys', self.captchaAns.keys())
            print('index', index)
            label = [self.captchaAns[str(i)] for i in index]
            label_df = pd.DataFrame({'index': index, 'label': label})
            pd.DataFrame(label_df).to_csv(saveFilePath, index=False)
            QMessageBox.information(self, '提示', '保存成功！')
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = Main()
    MainWindow.show()
    sys.exit(app.exec_())
