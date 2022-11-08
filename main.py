import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QFileDialog, QMessageBox, QInputDialog, QWidget
from PyQt5 import uic, QtMultimedia, QtCore
from PyQt5.QtGui import QIcon
import sqlite3
import eyed3
# библиотека для обработки нажатий клавиатуры
import keyboard
 

# класс основного окна
class Player(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)
        self.con = sqlite3.connect('music.sqlite3')
        self.cur = self.con.cursor()
        # загружаем стандартный плейлист "Мне нравится"
        tracks = self.cur.execute('''SELECT name, artist FROM Loving_Tracks''').fetchall()
        self.listWidget.clear()

        for m in tracks:
            listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
            self.listWidget.addItem(listWidgetItem)
            self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
            self.listWidget.itemClicked.connect(self.play_track)

        self.length.setText(f'Всего: {self.listWidget.count()}')

        self.is_playing = False
        self.track_row = 0
        self.add_track_but.clicked.connect(self.add_track_to_playlist)
        self.playlist = 'Loving_tracks'
        self.make_playlist_but.clicked.connect(self.make_playlist)
        self.player = QtMultimedia.QMediaPlayer()
        self.slider.setMinimum(0)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.player.positionChanged.connect(self.position_changed)
        self.player.mediaStatusChanged.connect(self.initPlayer)
        self.player.durationChanged.connect(self.duration_changed)
        self.play.clicked.connect(self.stop_track)
        self.selected_item = None
        self.next.clicked.connect(self.play_next_track)
        self.previous.clicked.connect(self.play_prev_track)
        self.repeat_but.clicked.connect(self.repeat)
        self.repeat_value = 1
        self.open_playlist.clicked.connect(self.open)
        self.plus10.clicked.connect(self.rewind_forward)
        self.minus10.clicked.connect(self.rewind_back)
        self.hook = keyboard.on_press(self.keyboardEventReceived)

    # функция выбора песни в плейлисте для дальнейшей работы с ним
    def play_track(self, item):
        text = item.text().split(' - ')
        artist = text[0]
        name = text[1]
        queue = f'SELECT location FROM {self.playlist} WHERE name = ? AND artist = ?'
        res = self.cur.execute(queue, (name, artist)).fetchall()
        location = res[0][0]
        self.player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl(location)))

    #добавление трека в плейлист
    def add_track_to_playlist(self):
        try:
            track_path = QFileDialog.getOpenFileName(self, 'Выбрать трек', '')[0]

            if len(track_path) != 0:
                track_info = eyed3.load(track_path)
                artist = track_info.tag.artist
                name = track_info.tag.title
                res = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()
                
                for m in res:
                    if m[0] == name and m[1] == artist:
                        raise TrackAlreadyExists

                duration = round(track_info.info.time_secs)
                queue = f'INSERT INTO {self.playlist} VALUES (?, ?, ?, ?)'
                self.cur.execute(queue, (name, artist, duration, track_path)).fetchall()
                name = ''
                name += self.playlist
                self.cur.execute(f'UPDATE Playlists SET length = length + 1 WHERE title="{name}"')
                self.con.commit()
                self.listWidget.clear()

                #заполняем виджет по новой

                tracks = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()

                for m in tracks:
                    listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
                    self.listWidget.addItem(listWidgetItem)
                    self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
                    self.listWidget.itemClicked.connect(self.play_track)

                self.length.setText(f'Всего: {self.listWidget.count()}')
        
        # обрабатываем тот случай, когда такой трек уже имеется в плейлисте
        except TrackAlreadyExists:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Трек уже в этом плейлисте!")
            ex = error_msg.exec()              

    # функция удаления трека из плейлиста
    def remove_track_from_playlist(self, item):
        if len(item.text()) != 0:
            text = item.text().split(' - ')
            artist = text[0]
            name = text[1]
            valid = QMessageBox.question(
                self, '', "Действительно удалить трек из плейлиста?",
                QMessageBox.Yes, QMessageBox.No)

            if valid == QMessageBox.Yes:
                self.cur.execute(f'DELETE FROM {self.playlist} WHERE name=? AND artist=?', (name, artist)).fetchall()
                name = ''
                name += self.playlist
                self.cur.execute(f'UPDATE Playlists SET length = length - 1 WHERE title="{name}"')
                self.con.commit()
                self.player.stop()
            self.listWidget.clear()

            # обновляем виджет

            tracks = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()
            
            if tracks:
                
                for m in tracks:
                    listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
                    self.listWidget.addItem(listWidgetItem)
                    self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
                    self.listWidget.itemClicked.connect(self.play_track)

                self.length.setText(f'Всего: {self.listWidget.count()}')

        if self.listWidget.count() == 0:
            self.length.setText('Всего: 0')

    # создаем новый плейлист
    def make_playlist(self):
        try:
            name, ok_pressed = QInputDialog.getText(self, "Введите название плейлиста", 
                                                    "Создать новый плейлист")
            if ok_pressed:
                
                if name == 'Playlists':
                    raise sqlite3.OperationalError

                if len(name) > 30:
                    raise TooLong

                if len(name) != 0:
                    names = self.cur.execute('SELECT title From Playlists')

                    for m in names:
                        if m[0] == name or m[0] == 'Мне нравится':
                            raise PlaylistAlreadyExists

                    self.cur.execute(f'CREATE TABLE IF NOT EXISTS {name}(name STRING, artist STRING, duration INT, location STRING);')
                    self.con.commit()
                    self.playlist_name.setText(name)
                    self.playlist = name
                    tracks = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()
                    self.listWidget.clear()

                    # заполняем виджет

                    for m in tracks:
                        listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
                        self.listWidget.addItem(listWidgetItem)
                        self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
                        self.listWidget.itemClicked.connect(self.play_track)

                    self.length.setText(f'Всего: {self.listWidget.count()}')

                    queue = f'INSERT INTO Playlists(title,length) VALUES(?,0)'
                    self.cur.execute(queue, (name,)).fetchall()
                    self.con.commit()

        # обработка неправильного названия
        except sqlite3.OperationalError as e:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Некорректное название!")
            ex = error_msg.exec()  

        # обработка слишком длинного названия
        except TooLong:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Слишком длинное название!")
            ex = error_msg.exec() 

        # обработка повторяющегося названия
        except PlaylistAlreadyExists:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Плейлист с таким названием уже существует!")
            ex = error_msg.exec()                              

    # функция работы с плеером
    def initPlayer(self, state):
        if state == QtMultimedia.QMediaPlayer.LoadedMedia:
            self.slider.setMaximum(self.player.duration())

        elif state == QtMultimedia.QMediaPlayer.EndOfMedia:
            self.slider.setValue(0)

            if self.repeat_value == 2:
                row = self.listWidget.currentRow()
                item = self.listWidget.item(row)
                item.setSelected(True)
                self.listWidget.setCurrentRow(row)
                self.play_track(item)
                self.player.play()
                self.play.setIcon(QIcon('stop.png'))
                self.is_playing = True

            else:
                self.player.stop()

                if self.listWidget.currentRow() + 1 != self.listWidget.count():
                    row = self.listWidget.currentRow() + 1
                    item = self.listWidget.item(row)
                    item.setSelected(True)
                    self.play_track(item)
                    self.listWidget.setCurrentRow(row)
                    self.player.play()
                    self.play.setIcon(QIcon('stop.png'))
                    self.is_playing = True

                else:
                    row = 0
                    item = self.listWidget.item(row)
                    item.setSelected(True)
                    self.play_track(item)
                    self.listWidget.setCurrentRow(row)
                    self.player.play()
                    self.play.setIcon(QIcon('stop.png'))
                    self.is_playing = True

        elif state == QtMultimedia.QMediaPlayer.NoMedia or state == QtMultimedia.QMediaPlayer.InvalidMedia:
            self.slider.setValue(0)

    # задаем позицию слайдеру в зависимости от времени
    def position_changed(self, position):
        self.slider.blockSignals(True)
        self.slider.setValue(position)
        self.slider.blockSignals(False)
        self.playing_time.setText(self.mmss(position))

    # длительность трека
    def duration_changed(self, duration):
        self.slider.setMaximum(duration)
        self.duration_time.setText(self.mmss(duration))

    # преобразование миллисекунд в формат минуты:секунды
    def mmss(self, ms):
        s = round(ms / 1000)
        m, s = divmod(s, 60)
        return "%d:%02d" % (m, s)

    # ставим трек на паузу   
    def stop_track(self):
        if self.is_playing == False:
            self.player.play()
            self.play.setIcon(QIcon('stop.png'))
            self.is_playing = True

        else:
            self.player.pause()
            self.play.setIcon(QIcon('play.png'))
            self.is_playing = False

    # включаем следующиий трек
    def play_next_track(self):
        if self.listWidget.currentRow() == 0 and not self.is_playing:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Ни один трек не выбран!")
            ex = error_msg.exec()


        elif self.listWidget.currentRow() == self.listWidget.count() - 1:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Впереди ничего нет!")
            ex = error_msg.exec()

        else:
            row = self.listWidget.currentRow() + 1
            item = self.listWidget.item(row)
            item.setSelected(True)
            print(row)
            self.play_track(item)
            self.listWidget.setCurrentRow(row)
            self.player.play()
            self.play.setIcon(QIcon('stop.png'))
            self.is_playing = True

    # включаем предыдущий трек
    def play_prev_track(self):
        if self.listWidget.currentRow() == 0:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText("Ни один трек не выбран!")
            ex = error_msg.exec()

        else:
            row = self.listWidget.currentRow() - 1
            item = self.listWidget.item(row)
            item.setSelected(True)
            self.play_track(item)
            self.listWidget.setCurrentRow(row)
            self.player.play()
            self.play.setIcon(QIcon('stop.png'))
            self.is_playing = True

    # включаем или отключаем повторение трека
    def repeat(self):
        if self.repeat_value == 1:
            self.repeat_but.setIcon(QIcon('repeat2.png'))
            self.repeat_value += 1

        else:
            self.repeat_but.setIcon(QIcon('repeat1.png'))
            self.repeat_value -= 1

    # открываем меню с плейлистами
    def open(self):
        self.playlists_window = Playlist_Window()
        self.playlists_window.signal.connect(self.is_closed)
        self.playlists_window.show()

    def is_closed(self):
        if self.playlists_window.removed_name != '':
            self.playlist = 'Loving_tracks'
            tracks = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()
            self.listWidget.clear()
            self.playlist_name.setText('Мне нравится')

            for m in tracks:
                listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
                self.listWidget.addItem(listWidgetItem)
                self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
                self.listWidget.itemClicked.connect(self.play_track)

            self.length.setText(f'Всего: {self.listWidget.count()}')  

        if self.playlists_window.playlist != '':
            self.playlist = self.playlists_window.playlist

            if self.playlist == 'Loving_Tracks':
                self.playlist_name.setText('Мне нравится')

            else:
                self.playlist_name.setText(self.playlist)
            
            print(self.playlist)
            tracks = self.cur.execute(f'SELECT name, artist FROM {self.playlist}').fetchall()
            self.listWidget.clear()

            for m in tracks:
                listWidgetItem = QListWidgetItem(f'{m[1]} - {m[0]}')
                self.listWidget.addItem(listWidgetItem)
                self.listWidget.itemDoubleClicked.connect(self.remove_track_from_playlist)
                self.listWidget.itemClicked.connect(self.play_track)

            self.length.setText(f'Всего: {self.listWidget.count()}')  

    # перемотать трек на 10 секунд вперед
    def rewind_forward(self):
        if self.is_playing:
            position = self.player.position()
            self.player.setPosition(position + 10000)

    # перемотать трек на 10 секунд назад
    def rewind_back(self):
        if self.is_playing:
            position = self.player.position()

            if position >= 10000:
                self.player.setPosition(position - 10000)  

            else:
                self.player.setPosition(0)

    def keyboardEventReceived(self, event):
        if event.event_type == 'down':
            
            if event.name == 'right':
                self.rewind_forward()

            elif event.name == 'left':
                self.rewind_back()

            elif event.name == 'r':
                self.repeat()


# Класс меню с плейлистами
class Playlist_Window(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('playlist.ui', self)
        self.con = sqlite3.connect('music.sqlite3')
        self.cur = self.con.cursor()
        tracks = self.cur.execute('''SELECT title, length FROM Playlists''').fetchall()
        self.listWidget.clear()

        # обновляем меню
        for m in tracks:
            listWidgetItem = QListWidgetItem(f'{m[0]} \t\t\t Треков: {m[1]}')
            self.listWidget.addItem(listWidgetItem)
            self.listWidget.itemClicked.connect(self.choose_playlist_item)

        self.length.setText(f'Всего: {self.listWidget.count()}')

        self.choose.clicked.connect(self.choose_playlist)
        self.name = ''
        self.playlist = ''
        self.delete_track_but.clicked.connect(self.delete_playlist)
        self.delete_track_but.setEnabled(False)
        self.removed_name = ''

    signal = QtCore.pyqtSignal(str)

    def choose_playlist_item(self, item):
        name = item.text()
        self.name = name
        self.delete_track_but.setEnabled(True)
        self.delete_track_but.setIcon(QIcon('delete.png'))

    def sendEditContent(self):
        content = '1'
        self.signal.emit(content)

    def closeEvent(self, event):
        self.sendEditContent()

    def choose_playlist(self):
        self.playlist = self.name.split('\t')[0].strip()
        self.close()

    # удаляем плейлист
    def delete_playlist(self):
        try:
            if len(self.name) != 0:
                text = self.name.split('\t')
                name = text[0].strip()
                valid = QMessageBox.question(
                    self, '', "Действительно удалить плейлист",
                    QMessageBox.Yes, QMessageBox.No)

                if valid == QMessageBox.Yes:

                    if name != 'Loving_Tracks':
                        self.cur.execute(f'DELETE FROM Playlists WHERE title="{name}"').fetchall()
                        self.removed_name = name
                        self.con.commit()
                        tracks = self.cur.execute('''SELECT title, length FROM Playlists''').fetchall()
                        self.listWidget.clear()

                        for m in tracks:
                            listWidgetItem = QListWidgetItem(f'{m[0]} \t\t\t Треков: {m[1]}')
                            self.listWidget.addItem(listWidgetItem)
                            self.listWidget.itemClicked.connect(self.choose_playlist_item)

                        self.length.setText(f'Всего: {self.listWidget.count()}')

                    else:
                        raise BadNameToRemove

        # сообщаем, что плейлист "Мне нравится" удалить нельзя
        except BadNameToRemove:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Ошибка!")
            error_msg.setText('Нельзя удалить плейлист "Мне нравится"!')
            ex = error_msg.exec()       


# ошибки
class TooLong(Exception):
    pass


class PlaylistAlreadyExists(Exception):
    pass


class TrackAlreadyExists(Exception):
    pass

class BadNameToRemove(Exception):
    pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = Player()
    player.show()
    sys.exit(app.exec_())