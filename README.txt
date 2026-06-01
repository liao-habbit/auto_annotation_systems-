Rice Auto Annotation Tool 安裝說明（README）
系統需求

建議作業系統：

Windows 10 / Windows 11

建議 Python 版本：

Python 3.10.x

不建議使用：

Python 3.12
Python 3.13

因為部分 YOLO / OpenCV 套件可能不相容。

STEP 1 安裝 Python 3.10

請至 Python 官方網站下載：

Python Downloads

下載：

Python 3.10.x
安裝時務必勾選

安裝畫面中：

☑ Add Python to PATH

非常重要。

安裝完成後測試

開啟：

CMD（命令提示字元）

輸入：

python --version

如果看到：

Python 3.10.x

代表安裝成功。

STEP 2 安裝套件

進入本專案資料夾：

cd /d 專案資料夾位置

例如：

cd /d D:\Rice_Auto_Annotation
安裝 requirements

輸入：

pip install -r requirements.txt

第一次安裝可能需要數分鐘。

STEP 3 測試 Flask 與 YOLO

輸入：

python

然後：

from ultralytics import YOLO
from flask import Flask

如果沒有錯誤：

代表環境安裝成功

輸入：

exit()

離開 Python。

專案資料夾結構

請確認資料夾結構如下：

Rice_Auto_Annotation/
│
├── app.py
├── prepare_and_predict.py
├── clean_review_batch.py
├── requirements.txt
├── best.pt
│
├── Raw_Images/
├── images/
├── yolo_labels/
├── xml_output/
├── review_status/
│
├── static/
├── templates/
│
├── run_prepare_and_predict.bat
├── run_tool.bat
├── clean_review_batch.bat
日常使用流程
STEP 1

把新照片放入：

Raw_Images
STEP 2

雙擊：

run_prepare_and_predict.bat

系統會自動：

1. 修正 EXIF 方向
2. 重新編流水號
3. YOLO 自動標註
4. 產生 labels
STEP 3

雙擊：

run_tool.bat

瀏覽器會自動開啟：

http://127.0.0.1:5000

即可開始專家審核。

審核完成後

XML 會輸出至：

xml_output

YOLO labels 會輸出至：

yolo_labels
常見問題
問題：找不到 flask

錯誤：

ModuleNotFoundError: No module named 'flask'

解決方法：

pip install -r requirements.txt
問題：python 不是內部或外部命令

代表：

Python 未加入 PATH

請重新安裝 Python 並勾選：

☑ Add Python to PATH
問題：YOLO 找不到圖片

請確認：

Raw_Images 裡面有 JPG 照片
注意事項
建議照片先使用手機原始照片
系統會自動修正 EXIF 旋轉方向
請勿手動修改 images 內檔名
XML 內會保留原始照片名稱資訊
開發者建議

若未來要重新訓練模型：

建議：

專家審核完成後的 XML
+
Normalize 後的 images

作為正式訓練資料集。