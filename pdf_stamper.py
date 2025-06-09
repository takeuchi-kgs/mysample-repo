#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from datetime import datetime
from pathlib import Path
from typing import List
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import io


class PDFStamper:
    def __init__(self):
        # 日本語フォントを登録
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            self.font_name = 'HeiseiKakuGo-W5'
        except:
            self.font_name = 'Helvetica'
        
        self.stamp_text = "作業完了"
        self.processed_files = []
    
    def create_stamp_pdf(self, width: float, height: float) -> bytes:
        """スタンプ用のPDFを作成"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))
        
        # 現在の日付を取得
        today = datetime.now().strftime("%Y/%m/%d")
        
        # スタンプの位置（右上）
        x_pos = width - 2 * inch
        y_pos = height - 1 * inch
        
        # 背景（半透明の白い矩形）
        c.setFillColorRGB(1, 1, 1, alpha=0.8)
        c.rect(x_pos - 0.2 * inch, y_pos - 0.4 * inch, 1.8 * inch, 0.8 * inch, fill=1, stroke=0)
        
        # 枠線
        c.setStrokeColorRGB(0.8, 0, 0)
        c.setLineWidth(2)
        c.rect(x_pos - 0.2 * inch, y_pos - 0.4 * inch, 1.8 * inch, 0.8 * inch, fill=0, stroke=1)
        
        # テキスト
        c.setFillColorRGB(0.8, 0, 0)
        c.setFont(self.font_name, 12)
        c.drawString(x_pos, y_pos, self.stamp_text)
        c.setFont(self.font_name, 10)
        c.drawString(x_pos, y_pos - 0.2 * inch, today)
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def stamp_pdf(self, input_path: str, output_path: str) -> bool:
        """PDFにスタンプを追加"""
        try:
            with open(input_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # 最初のページのサイズを取得
                first_page = pdf_reader.pages[0]
                page_width = float(first_page.mediabox.width)
                page_height = float(first_page.mediabox.height)
                
                # スタンプPDFを作成
                stamp_pdf_bytes = self.create_stamp_pdf(page_width, page_height)
                stamp_pdf = PyPDF2.PdfReader(io.BytesIO(stamp_pdf_bytes))
                stamp_page = stamp_pdf.pages[0]
                
                # 全ページにスタンプを追加
                for page in pdf_reader.pages:
                    # スタンプを重ね合わせ
                    page.merge_page(stamp_page)
                    pdf_writer.add_page(page)
                
                # 出力ファイルに書き込み
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                return True
                
        except Exception as e:
            print(f"エラーが発生しました（{input_path}）: {e}")
            return False
    
    def process_pdf_files(self, input_dir: str) -> List[str]:
        """指定ディレクトリ内のPDFファイルを処理"""
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"ディレクトリが見つかりません: {input_dir}")
            return []
        
        pdf_files = list(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"PDFファイルが見つかりません: {input_dir}")
            return []
        
        processed_files = []
        
        for pdf_file in pdf_files:
            print(f"処理中: {pdf_file.name}")
            
            # 同じファイルに上書き保存
            if self.stamp_pdf(str(pdf_file), str(pdf_file)):
                processed_files.append(str(pdf_file))
                print(f"完了: {pdf_file.name}")
            else:
                print(f"失敗: {pdf_file.name}")
        
        self.processed_files = processed_files
        return processed_files
    
    def move_processed_files(self, destination_dir: str) -> bool:
        """処理済みファイルを指定ディレクトリに移動"""
        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        moved_count = 0
        for file_path in self.processed_files:
            try:
                file_name = Path(file_path).name
                dest_file = dest_path / file_name
                
                # ファイル名が重複する場合は番号を付加
                counter = 1
                while dest_file.exists():
                    name_parts = file_name.rsplit('.', 1)
                    if len(name_parts) == 2:
                        new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        new_name = f"{file_name}_{counter}"
                    dest_file = dest_path / new_name
                    counter += 1
                
                shutil.move(file_path, str(dest_file))
                moved_count += 1
                print(f"移動完了: {file_name} -> {dest_file}")
                
            except Exception as e:
                print(f"移動エラー ({file_path}): {e}")
        
        print(f"合計 {moved_count} ファイルを移動しました")
        return moved_count > 0


def main():
    stamper = PDFStamper()
    
    # 処理対象のディレクトリを指定
    input_directory = input("PDFファイルがあるディレクトリのパスを入力してください: ").strip()
    
    if not input_directory:
        print("ディレクトリパスが入力されていません")
        return
    
    # PDFファイルを処理
    processed_files = stamper.process_pdf_files(input_directory)
    
    if processed_files:
        print(f"\n{len(processed_files)} 個のファイルを処理しました")
        
        # 移動先ディレクトリを指定
        move_files = input("\n処理済みファイルを別のディレクトリに移動しますか？ (y/n): ").strip().lower()
        
        if move_files in ['y', 'yes']:
            dest_directory = input("移動先ディレクトリのパスを入力してください: ").strip()
            if dest_directory:
                stamper.move_processed_files(dest_directory)
            else:
                print("移動先ディレクトリが指定されていません")
    else:
        print("処理されたファイルがありません")


if __name__ == "__main__":
    main()