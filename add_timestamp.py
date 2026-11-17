import os
import re
import shutil
import tempfile
import numpy as np
from datetime import datetime
import cv2
from PIL import Image, ImageDraw, ImageFont

def parse_timestamp(filename):
    """ファイル名から17桁または14桁のタイムスタンプを抽出してdatetimeにする関数"""
    match = re.search(r'\d{17}', filename)
    if not match:
        match = re.search(r'\d{14}', filename)
        if not match:
            return None
    ts_str = match.group()
    try:
        if len(ts_str) == 17:
            return datetime.strptime(ts_str + "000", "%Y%m%d%H%M%S%f")
        else:
            return datetime.strptime(ts_str, "%Y%m%d%H%M%S")
    except ValueError:
        return None

def process_and_create_video(folder_path, temp_video_path, fps=24):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    
    if not os.path.exists(folder_path):
        print(f"\n【エラー】指定されたフォルダが見つかりません:\n{folder_path}")
        return False

    # 画像の抽出と日時の解析
    image_tasks = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(valid_extensions):
            dt = parse_timestamp(f)
            if dt:
                image_tasks.append((f, dt))
                
    if not image_tasks:
        print("\n【エラー】タイムスタンプ名（数字）を持つ画像ファイルが見つかりませんでした。")
        return False

    # 時系列（古い順）にソート
    image_tasks.sort(key=lambda x: x[1])
    base_time = image_tasks[0][1]
    print(f"\n基準日時（0秒）: {base_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    
    # 最初の一枚を読み込んで動画の基準サイズを決定
    first_img_path = os.path.join(folder_path, image_tasks[0][0])
    
    # 【修正点1】日本語パス対応：cv2.imread の代わりに numpy と cv2.imdecode を使用
    img_array = np.fromfile(first_img_path, dtype=np.uint8)
    first_frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if first_frame is None:
        print(f"エラー: 最初の画像 '{image_tasks[0][0]}' を読み込めませんでした。")
        return False
        
    height, width, _ = first_frame.shape
    video_size = (width, height)
    
    # 動画ライターの初期化
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(temp_video_path, fourcc, fps, video_size)
    
    print(f"\n【上書き処理＆動画化】を開始します... (総フレーム数: {len(image_tasks)})")
    
    for filename, dt in image_tasks:
        img_path = os.path.join(folder_path, filename)
        
        # 経過秒数の計算
        delta = dt - base_time
        total_seconds = delta.total_seconds()
        text_to_draw = "0.000s" if total_seconds == 0 else f"+{total_seconds:.3f}s"
        
        try:
            # Pillowで画像を開いて文字入れ
            with Image.open(img_path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                
                if img.size != video_size:
                    img = img.resize(video_size)
                    
                draw = ImageDraw.Draw(img)
                w, h = img.size
                
                # 文字サイズと位置の調整
                font_size = max(20, int(min(w, h) * 0.05))
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()
                    
                bbox = draw.textbbox((0, 0), text_to_draw, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                margin = int(min(w, h) * 0.03)
                x = w - text_w - margin
                y = h - text_h - margin
                
                # 黒い縁取り
                shadow = max(1, font_size // 15)
                for ax in [-shadow, 0, shadow]:
                    for ay in [-shadow, 0, shadow]:
                        draw.text((x + ax, y + ay), text_to_draw, font=font, fill=(0, 0, 0))
                # 黄色のメイン文字
                draw.text((x, y), text_to_draw, font=font, fill=(255, 215, 0))
                
                # 画像の保存
                img.save(img_path, quality=95)
                
                # 動画へ書き込むために Pillow から OpenCV 形式へ逆変換
                cv2_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                video_writer.write(cv2_img)
                print(f"上書き＆コマ追加完了: {filename} -> {text_to_draw}")
                
        except Exception as e:
            print(f"警告: {filename} の処理をスキップしました: {e}")
            continue
            
    video_writer.release()
    return True

if __name__ == "__main__":
    print("==================================================")
    print(" 動画化＆写真に秒数を【上書き】したい写真フォルダのパスを入力してください。")
    print("==================================================")
    
    user_input = input("フォルダのパス ＞ ")
    IMAGE_FOLDER = user_input.strip().strip('"').strip("'")
    
    # 【修正点2】OpenCVの日本語パス書き出しエラーを防ぐため、OSの標準一時フォルダ（Temp）を作業場所に指定
    TEMP_VIDEO_NAME = "_temp_combined_video.mp4"
    temp_video_path = os.path.join(tempfile.gettempdir(), TEMP_VIDEO_NAME)
    
    FPS = 24                          
    
    if process_and_create_video(IMAGE_FOLDER, temp_video_path, FPS):
        print("\n--------------------------------------------------")
        filename_input = input("動画作成＆写真の上書きが完了しました。動画のファイル名は何にしますか？ ＞ ")
        print("--------------------------------------------------")
        
        filename_input = filename_input.strip()
        if not filename_input:
            filename_input = "output_timestamp_movie"
            
        if not filename_input.lower().endswith('.mp4'):
            filename_input += '.mp4'
            
        final_video_path = os.path.join(IMAGE_FOLDER, filename_input)
        
        try:
            if os.path.exists(final_video_path):
                os.remove(final_video_path)
            
            # 【修正点3】別ドライブ間の移動に対応するため、os.replace から shutil.move に変更
            shutil.move(temp_video_path, final_video_path)
            
            print(f"\n【完了】動画を画像フォルダ内に保存しました:\n{final_video_path}")
            print("元の写真ファイルへの秒数上書きもすべて完了しています。")
        except Exception as e:
            print(f"\n【エラー】ファイル名の変更または移動に失敗しました: {e}")
            print(f"動画は次の暫定名で一時フォルダ内に残っています: {temp_video_path}")
            
    input("\nEnterキーを押すと終了します...")