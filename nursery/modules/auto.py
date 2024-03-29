import signal
import time
from multiprocessing import Process, Queue, active_children

import pyautogui

from nursery.modules.config import GRID_GAP, GRID_SIZE, OFFSET_TOP, OFFSET_X


def _getMousePosByGridPos(appInfo, gridPos, needOffset=False):
    (appX, appY, scale) = appInfo
    #将gridPoS元组解包成x和y两个变量
    y, x = gridPos

    scaledOffsetX = OFFSET_X * scale
    scaledOffsetTop = OFFSET_TOP * scale
    scaledGridSize = GRID_SIZE * scale
    scaledGridGap = GRID_GAP * scale

    # Offset need add back the gap
    mouseX = appX + (
        scaledOffsetX + x * scaledGridSize + scaledGridGap * x + scaledGridGap
    )
    mouseY = appY + (
        scaledOffsetTop + y * scaledGridSize + scaledGridGap * y + scaledGridGap
    )
   #如果needOffset为true，则将鼠标位置调整到网格中心
    if needOffset:
        mouseX += int(scaledGridSize / 2)
        mouseY += int(scaledGridSize / 2)

    return [mouseX, mouseY]


def _queueTask(chessboard, taskQueue):
    row = len(chessboard)
    col = len(chessboard[0])
    #和为10
    TARGET_SUM = 10

    # 搜索的层级
    surroundingLevel = 1
    found = False
    try:
        while True:
            # 棋盘大小为 16x10
            #搜索层级大于16时停止
            if surroundingLevel > 16:
              surroundingLevel=1
                #矩阵元素全为0
            if all(all(element == 0 for element in row) for row in chessboard):
                break



            # 遍历棋盘中的每个位置
            for i in range(0, row):
                for j in range(0, col):
                    center = chessboard[i][j]

                    # 当前为0则跳过
                    if center == 0:
                        continue

                    # Reset found flag
                    found = False
                    nums = [center]
                    # 3点钟方向顺时针搜索
                    for level in range(1, surroundingLevel + 1):
                        if j + level < col:
                            next = chessboard[i][j + level]
                            nums.append(next)
                            #满足和为10
                            if sum(nums) == TARGET_SUM:
                                taskQueue.put(([i, j], [i, j + level]), False)


                                # 情况当前位置的值，设置为0
                                for clean in range(0, level + 1):
                                    chessboard[i][j + clean] = 0
                                found = True
                                break
                            if sum(nums) > TARGET_SUM:
                                break

                    if found:
                        continue

                    nums = [center]
                    # 搜索6点钟方向
                    for level in range(1, surroundingLevel + 1):
                        if i + level < row:
                            next = chessboard[i + level][j]
                            nums.append(next)

                            if sum(nums) == TARGET_SUM:
                                taskQueue.put(([i, j], [i + level, j]), False)

                                # 情况当前位置的值，设置为0
                                for clean in range(0, level + 1):
                                    chessboard[i + clean][j] = 0
                                break
                            if sum(nums) > TARGET_SUM:
                                break

            # Wait for next loop
            surroundingLevel += 1
            time.sleep(1)
    except:  # noqa: E722
        pass
def _processTask(appInfo, taskQueue):
    # B'z the task data is much more faster then the gui
    # So it just works, lol
    guiStarted = False
    while True:
        try:
            #尝试从队列中获取任务，如果队列为空则抛出异常
            task = taskQueue.get(block=False)
            guiStarted = True
            # 解包任务元组，得到起始单元格和目标单元格
            fromCell, toCell = task
            # 计算起始鼠标位置和目标鼠标位置
            fromPos = _getMousePosByGridPos(appInfo, fromCell)
            # Add offset to make sure across the cell
            toPos = _getMousePosByGridPos(appInfo, toCell, True)
            # 打印起始和目标单元格以及拖拽信息
            print("fromCell", fromCell, "toCell", toCell)
            print("Drag from %s to %s" % (fromPos, toPos))
            # 移动鼠标到起始位置，稍作等待后拖拽到目标位置
            pyautogui.moveTo(fromPos)
            time.sleep(0.06)
            pyautogui.dragTo(toPos, duration=0.3)
        except:  # noqa: E722
            # Done all tasks.
            if guiStarted:
                break


def _stopProcess(signal, frame):
    print("Caught Ctrl+C, stopping processes...")
    for p in active_children():
        p.terminate()
    exit(0)


def auto(appInfo, matrix):
    chessboard = matrix

    print(chessboard)

     #创建一个任务队列
    taskQueue = Queue()
    #创建一个进程队列
    proc = []

    # 创建并启动一个进程，该进程用于向任务队列添加任务
    queueTask = Process(target=_queueTask, args=(chessboard, taskQueue))
    queueTask.start()
    proc.append(queueTask)

    # 创建并启动一个进程，该进程用于处理任务队列中的任务
    processTask = Process(
        target=_processTask,
        args=(
            appInfo,
            taskQueue,
        ),
    )
    processTask.start()
    proc.append(processTask)

    # 注册信号处理函数，用于捕捉 Ctrl-C 信号
    signal.signal(signal.SIGINT, _stopProcess)

    for p in proc:
        p.join()
