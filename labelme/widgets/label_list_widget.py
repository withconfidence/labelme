import decimal

from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtGui import QPalette
from qtpy import QtWidgets
from qtpy.QtWidgets import QStyle


# https://stackoverflow.com/a/2039745/4158863
class HTMLDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HTMLDelegate, self).__init__()
        self.doc = QtGui.QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()

        options = QtWidgets.QStyleOptionViewItem(option)

        self.initStyleOption(options, index)
        self.doc.setHtml(options.text)
        options.text = ""

        style = (
            QtWidgets.QApplication.style()
            if options.widget is None
            else options.widget.style()
        )
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(
                    QPalette.Active, QPalette.HighlightedText
                ),
            )
        else:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(QPalette.Active, QPalette.Text),
            )

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)

        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)

        thefuckyourshitup_constant = 4
        margin = (option.rect.height() - options.fontMetrics.height()) // 2
        margin = margin - thefuckyourshitup_constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        thefuckyourshitup_constant = 4
        return QtCore.QSize(
            self.doc.idealWidth(),
            self.doc.size().height() - thefuckyourshitup_constant,
        )


class LabelListWidgetItem(QtGui.QStandardItem):
    def __init__(self, text=None, shape=None):
        super(LabelListWidgetItem, self).__init__()
        self.setText(text or "")
        self.setShape(shape)

        self.setCheckable(True)
        self.setCheckState(Qt.Checked)
        self.setEditable(False)
        self.setTextAlignment(Qt.AlignBottom)
        # self.model().setColumnCount(2)
        # self.model().setHorizontalHeaderLabels(["Label", "Size"])

    def clone(self):
        return LabelListWidgetItem(self.text(), self.shape())
        # return [LabelListWidgetItem(self.text(), self.shape()), QtGui.QStandardItem("area")]

    def setShape(self, shape):
        self.setData(shape, Qt.UserRole)

    def shape(self):
        return self.data(Qt.UserRole)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.text())


class StandardItemModel(QtGui.QStandardItemModel):

    itemDropped = QtCore.Signal()

    def removeRows(self, *args, **kwargs):
        ret = super().removeRows(*args, **kwargs)
        self.itemDropped.emit()
        return ret


class LabelListWidget(QtWidgets.QTreeView):
# class LabelListWidget(QtWidgets.QListView):

    itemDoubleClicked = QtCore.Signal(LabelListWidgetItem)
    itemSelectionChanged = QtCore.Signal(list, list)

    def __init__(self):
        super(LabelListWidget, self).__init__()
        self._selectedItems = []

        self.setWindowFlags(Qt.Window)
        # self.setColumnCount(2)
        standard_model = StandardItemModel()
        self.setModel(standard_model)
        self.model().setItemPrototype(LabelListWidgetItem())

        self.setItemDelegate(HTMLDelegate())

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # self.setSelectionMode(QtWidgets.QAbstractItemView.SelectRows)

        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        # self.doubleClicked.connect(self.itemDoubleClickedEvent)
        self.selectionModel().selectionChanged.connect(
            self.itemSelectionChangedEvent
        )

    def __len__(self):
        return self.model().rowCount()

    def __getitem__(self, i):
        return self.model().item(i)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def measure_size(self, points, ratio=1):
        # for x, y in points:

        n = len(points)  # of corners
        if n != 2:
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += points[i].x() * points[j].y()
                area -= points[j].x() * points[i].y()
            area = abs(area) / 2.0
            actual_area = area * pow(ratio, 2)
            actual_area_string = f"{decimal.Decimal(actual_area):.3E}"
            return actual_area_string
        else:
            length = pow(pow(points[0].x() - points[1].x(), 2) + pow(points[0].x() - points[1].x(), 2), 0.5)
            actual_length = length * ratio
            actual_length = f"{decimal.Decimal(actual_length):.3E}"
            return actual_length

    @property
    def itemDropped(self):
        return self.model().itemDropped

    @property
    def itemChanged(self):
        return self.model().itemChanged

    def itemSelectionChangedEvent(self, selected, deselected):
        selected = [self.model().itemFromIndex(i) for i in selected.indexes()]
        deselected = [
            self.model().itemFromIndex(i) for i in deselected.indexes()
        ]
        self.itemSelectionChanged.emit(selected, deselected)

    def itemDoubleClickedEvent(self, index):
        self.itemDoubleClicked.emit(self.model().itemFromIndex(index))

    def selectedItems(self):
        return [self.model().itemFromIndex(i) for i in self.selectedIndexes()]

    def scrollToItem(self, item):
        self.scrollTo(self.model().indexFromItem(item))

    def addItem(self, item):
        # item = items[0]
        if not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem")
        points = item.shape().points
        if len(points) == 2:
            shape_type = "Line"
        else:
            shape_type = "Polygon"
        area = self.measure_size(points)

        # print(f"{area=}")
        self.model().appendRow([item, QtGui.QStandardItem(shape_type), QtGui.QStandardItem(area)])
        item.setSizeHint(self.itemDelegate().sizeHint(None, None))
        self.model().setColumnCount(3)
        self.model().setHorizontalHeaderLabels(["Label", "Shape", "Size"])
        self.setHeaderHidden(False)

    def removeItem(self, item):
        index = self.model().indexFromItem(item)
        self.model().removeRows(index.row(), 1)

    def selectItem(self, item):
        index = self.model().indexFromItem(item)
        self.selectionModel().select(index, QtCore.QItemSelectionModel.Select)

    def findItemByShape(self, shape):
        for row in range(self.model().rowCount()):
            item = self.model().item(row, 0)
            if item.shape() == shape:
                return item
        raise ValueError("cannot find shape: {}".format(shape))

    def clear(self):
        self.model().clear()
