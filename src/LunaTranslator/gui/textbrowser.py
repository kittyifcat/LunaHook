from qtsymbols import *
from myutils.config import globalconfig
import importlib, copy, os, platform
from traceback import print_exc
from gui.usefulwidget import WebviewWidget
from hiraparse.basehira import basehira


class TextType:
    Origin = 0
    Translate = 1
    Info = 2
    Error_origin = 3
    Error_translator = 4


class ColorControl:
    RAW_TEXT_COLOR = 0
    TS_COLOR = 1
    ERROR_COLOR = 2
    COLOR_DEFAULT = 2
    KANA_COLOR = 3
    FENCI_COLOR = 4

    def __init__(self, T, klass=None):
        self.type = T
        self.klass = klass

    def get(self):
        if self.type == self.RAW_TEXT_COLOR:
            return globalconfig["rawtextcolor"]
        if self.type == self.KANA_COLOR:
            return globalconfig["jiamingcolor"]
        if self.type == self.ERROR_COLOR:
            return "red"
        if self.type == self.COLOR_DEFAULT:
            return "black"
        if self.type == self.TS_COLOR:
            return globalconfig["fanyi"].get(self.klass, {}).get("color", "black")

    def asklass(self):
        if self.type == self.RAW_TEXT_COLOR:
            return "ColorControl_RAW_TEXT_COLOR"
        if self.type == self.KANA_COLOR:
            return "ColorControl_KANA_COLOR"
        if self.type == self.ERROR_COLOR:
            return "ColorControl_ERROR_COLOR"
        if self.type == self.COLOR_DEFAULT:
            return "ColorControl_COLOR_DEFAULT"

    def _tuple_(self):
        if self.klass:
            return (self.type, self.klass)
        return self.type

    def __repr__(self):
        return str(self._tuple_())

    def __hash__(self):
        return self._tuple_().__hash__()

    def __eq__(self, value):
        return self._tuple_() == value._tuple_()


class TranslateColor(ColorControl):
    def __init__(self, klass):
        super().__init__(ColorControl.TS_COLOR, klass)

    def get(self):
        return globalconfig["fanyi"].get(self.klass, {}).get("color", "black")

    def asklass(self):
        return "ColorControl_TS_COLOR_{}".format(self.klass)


class FenciColor(ColorControl):
    def __init__(self, word):
        self.isdeli = word.get("isdeli", False)
        self.cixing = word.get("cixing", None)
        super().__init__(ColorControl.FENCI_COLOR, (self.isdeli, self.cixing))

    def _randomcolor_1(self):
        if self.isdeli:
            return None
        if not globalconfig["show_fenci"]:
            return None
        c = QColor("white")
        if self.cixing:
            try:
                if globalconfig["cixingcolorshow"][self.cixing] == False:
                    return None
                c = QColor(globalconfig["cixingcolor"][self.cixing])
            except:
                pass
        return (c.red(), c.green(), c.blue(), globalconfig["showcixing_touming"] / 100)

    def get(self):
        color = self._randomcolor_1()
        if not color:
            color = (0, 0, 0, 0)
        r, g, b, a = color
        return "rgba({}, {}, {}, {})".format(r, g, b, a)

    def asklass(self):
        return "ColorControl_FENCI_COLOR_{}".format(
            str(self.klass).encode("utf8").hex()
        )


class SpecialColor:
    RawTextColor = ColorControl(ColorControl.RAW_TEXT_COLOR)
    ErrorColor = ColorControl(ColorControl.ERROR_COLOR)
    DefaultColor = ColorControl(ColorControl.COLOR_DEFAULT)
    KanaColor = ColorControl(ColorControl.KANA_COLOR)


class Textbrowser(QFrame):
    contentsChanged = pyqtSignal(QSize)
    dropfilecallback = pyqtSignal(str)

    def resizeEvent(self, event: QResizeEvent):
        self.textbrowser.resize(event.size())

    def _contentsChanged(self, size: QSize):
        self.contentsChanged.emit(size)

    def loadinternal(self, shoudong=False):
        __ = globalconfig["rendertext_using"]
        if self.curr_eng == __:
            return
        self.curr_eng = __
        size = self.size()
        if self.textbrowser:
            self.textbrowser.hide()
            self.textbrowser.contentsChanged.disconnect()
            self.textbrowser.dropfilecallback.disconnect()
            self.textbrowser.deleteLater()
        try:
            tb = importlib.import_module("rendertext." + __).TextBrowser
            self.textbrowser = tb(self)
        except:
            print_exc()
            if shoudong:
                WebviewWidget.showError()
            globalconfig["rendertext_using"] = "textbrowser"
            tb = importlib.import_module("rendertext.textbrowser").TextBrowser
            self.textbrowser = tb(self)

        if tuple(int(_) for _ in platform.version().split(".")[:2]) <= (6, 1):
            # win7不可以同时FramelessWindowHint和WA_TranslucentBackground，否则会导致无法显示
            # win8没问题
            self.window().setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground,
                globalconfig["rendertext_using"] == "textbrowser",
            )
        self.textbrowser.move(0, 0)
        self.textbrowser.setMouseTracking(True)
        self.textbrowser.contentsChanged.connect(self._contentsChanged)
        self.textbrowser.dropfilecallback.connect(self.normdropfilepath)
        self.textbrowser.resize(size)
        self.textbrowser.show()
        self.refreshcontent()

    def normdropfilepath(self, file):
        self.dropfilecallback.emit(os.path.normpath(file))

    def refreshcontent(self):
        self.textbrowser.refreshcontent_before()
        traces = self.trace.copy()
        self.clear()
        for t, trace in traces:
            if t == 0:
                self.append(*trace)
            elif t == 1:
                self.iter_append(*trace)
        self.textbrowser.refreshcontent_after()

    def __init__(self, parent):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.textbrowser = None
        self.cleared = True
        self.curr_eng = None
        self.trace = []
        self.loadinternal()

    def iter_append(
        self, iter_context_class, texttype: TextType, name, text, color: ColorControl
    ):
        self.trace.append((1, (iter_context_class, texttype, name, text, color)))
        self.cleared = False
        self.textbrowser.iter_append(iter_context_class, texttype, name, text, color)

    def append(self, texttype: TextType, name, text, tag, color: ColorControl):
        self.trace.append(
            (
                0,
                (
                    texttype,
                    name,
                    text,
                    copy.deepcopy(tag),
                    color,
                ),
            )
        )
        self.cleared = False
        self.textbrowser.append(
            texttype, name, text, basehira.parseastarget(tag), color
        )

    def clear(self):
        self.cleared = True
        self.trace.clear()
        self.textbrowser.clear()

    def setcolorstyle(self, _=None):
        self.textbrowser.setcolorstyle()

    def setfontstyle(self, _=None):
        self.textbrowser.setfontstyle()

    def showhidert(self, _):
        self.textbrowser.showhidert(_)

    def showhideclick(self, _):
        self.textbrowser.showhideclick(_)

    def showhidename(self, _):
        self.textbrowser.showhidename(_)

    def showatcenter(self, _):
        self.textbrowser.showatcenter(_)

    def showhidetranslate(self, _):
        self.textbrowser.showhidetranslate(_)

    def setselectable(self, _):
        self.textbrowser.setselectable(_)

    def showhideorigin(self, _):
        self.textbrowser.showhideorigin(_)

    def showhideerror(self, _):
        self.textbrowser.showhideerror(_)

    def resetstyle(self):
        self.textbrowser.resetstyle()
