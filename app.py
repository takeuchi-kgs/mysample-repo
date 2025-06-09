#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
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
import tempfile
import zipfile


class PDFStamper:
    def __init__(self):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            self.font_name = 'HeiseiKakuGo-W5'
        except:
            self.font_name = 'Helvetica'
        
        self.stamp_text = "作業完了"
        self.stamp_date = datetime.now().strftime("%Y/%m/%d")
    
    def set_stamp_date(self, date_str: str):
        """スタンプの日付を設定"""
        self.stamp_date = date_str
    
    def create_stamp_pdf(self, width: float, height: float) -> bytes:
        """スタンプ用のPDFを作成"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))
        
        x_pos = width - 2 * inch
        y_pos = height - 1 * inch
        
        c.setFillColorRGB(1, 1, 1, alpha=0.8)
        c.rect(x_pos - 0.2 * inch, y_pos - 0.4 * inch, 1.8 * inch, 0.8 * inch, fill=1, stroke=0)
        
        c.setStrokeColorRGB(0.8, 0, 0)
        c.setLineWidth(2)
        c.rect(x_pos - 0.2 * inch, y_pos - 0.4 * inch, 1.8 * inch, 0.8 * inch, fill=0, stroke=1)
        
        c.setFillColorRGB(0.8, 0, 0)
        c.setFont(self.font_name, 12)
        c.drawString(x_pos, y_pos, self.stamp_text)
        c.setFont(self.font_name, 10)
        c.drawString(x_pos, y_pos - 0.2 * inch, self.stamp_date)
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def stamp_pdf(self, input_bytes: bytes) -> bytes:
        """PDFバイトデータにスタンプを追加"""
        input_buffer = io.BytesIO(input_bytes)
        pdf_reader = PyPDF2.PdfReader(input_buffer)
        pdf_writer = PyPDF2.PdfWriter()
        
        first_page = pdf_reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
        
        stamp_pdf_bytes = self.create_stamp_pdf(page_width, page_height)
        stamp_pdf = PyPDF2.PdfReader(io.BytesIO(stamp_pdf_bytes))
        stamp_page = stamp_pdf.pages[0]
        
        for page in pdf_reader.pages:
            page.merge_page(stamp_page)
            pdf_writer.add_page(page)
        
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        return output_buffer.getvalue()


def main():
    st.set_page_config(
        page_title="PDF スタンプアプリ",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 PDF スタンプアプリ")
    st.markdown("複数のPDFファイルに「作業完了」スタンプと日付を追加するアプリです")
    
    # session_stateの初期化
    if 'stamper' not in st.session_state:
        st.session_state.stamper = PDFStamper()
    
    # サイドバーでオプション設定
    with st.sidebar:
        st.header("⚙️ 設定")
        today = datetime.now().strftime("%Y/%m/%d")
        st.info(f"今日の日付: {today}")
        
        st.markdown("### 📅 日付設定")
        
        # 日付入力フィールド
        date_input = st.text_input(
            "スタンプに使用する日付",
            value=st.session_state.stamper.stamp_date,
            placeholder="YYYY/MM/DD",
            help="スタンプに表示する日付を入力してください（例: 2024/12/25）"
        )
        
        # 設定ボタン
        if st.button("🔄 日付を設定", use_container_width=True):
            if date_input:
                st.session_state.stamper.set_stamp_date(date_input)
                st.success(f"日付を設定しました: {date_input}")
            else:
                st.error("日付を入力してください")
        
        st.markdown("---")
        
        st.markdown("### スタンプ仕様")
        st.markdown("- 位置: 各ページの右上")
        st.markdown("- 内容: 「作業完了」+ 日付")
        st.markdown("- デザイン: 赤い枠線と文字")
        st.markdown(f"- 現在の設定日付: **{st.session_state.stamper.stamp_date}**")
    
    # メインエリア
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 ファイルアップロード")
        uploaded_files = st.file_uploader(
            "PDFファイルを選択してください（複数選択可能）",
            type=['pdf'],
            accept_multiple_files=True,
            help="複数のPDFファイルを一度に選択できます"
        )
        
        if uploaded_files:
            st.success(f"📁 {len(uploaded_files)} 個のファイルが選択されました")
            
            # ファイル一覧表示
            with st.expander("選択されたファイル一覧", expanded=True):
                for i, file in enumerate(uploaded_files, 1):
                    file_size = len(file.getvalue()) / 1024  # KB
                    st.write(f"{i}. {file.name} ({file_size:.1f} KB)")
    
    with col2:
        st.header("🔄 処理実行")
        
        process_button = st.button(
            "📝 スタンプを追加",
            disabled=not uploaded_files,
            help="選択されたPDFファイルにスタンプを追加します",
            use_container_width=True
        )
        
        if process_button and uploaded_files:
            process_files(st.session_state.stamper, uploaded_files)


def process_files(stamper: PDFStamper, uploaded_files):
    """ファイル処理のメイン関数"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_files = []
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"処理中: {uploaded_file.name}")
        
        try:
            # ファイルバイトデータを取得
            file_bytes = uploaded_file.getvalue()
            
            # スタンプを追加
            stamped_bytes = stamper.stamp_pdf(file_bytes)
            
            # ファイル名に"_完了"を追加
            name_parts = uploaded_file.name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]}_完了.{name_parts[1]}"
            else:
                new_name = f"{uploaded_file.name}_完了"
            
            processed_files.append({
                'name': new_name,
                'data': stamped_bytes,
                'original_size': len(file_bytes),
                'processed_size': len(stamped_bytes)
            })
            
        except Exception as e:
            st.error(f"エラーが発生しました ({uploaded_file.name}): {str(e)}")
            continue
        
        # プログレスバー更新
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.progress(1.0)
    status_text.text("処理完了！")
    
    if processed_files:
        st.success(f"✅ {len(processed_files)} 個のファイルの処理が完了しました")
        
        # 結果表示
        show_results(processed_files)
        
        # ダウンロードセクション
        create_download_section(processed_files)


def show_results(processed_files):
    """処理結果を表示"""
    st.header("📊 処理結果")
    
    with st.expander("処理済みファイル詳細", expanded=True):
        for i, file_info in enumerate(processed_files, 1):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{i}. {file_info['name']}**")
            with col2:
                st.write(f"元サイズ: {file_info['original_size']/1024:.1f} KB")
            with col3:
                st.write(f"処理後: {file_info['processed_size']/1024:.1f} KB")


def create_download_section(processed_files):
    """ダウンロードセクションを作成"""
    st.header("💾 ダウンロード")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 個別ダウンロード")
        for file_info in processed_files:
            st.download_button(
                label=f"📥 {file_info['name']}",
                data=file_info['data'],
                file_name=file_info['name'],
                mime="application/pdf",
                use_container_width=True
            )
    
    with col2:
        st.subheader("📦 一括ダウンロード")
        if len(processed_files) > 1:
            # ZIPファイル作成
            zip_buffer = create_zip_file(processed_files)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"processed_pdfs_{timestamp}.zip"
            
            st.download_button(
                label="📦 全ファイルをZIPでダウンロード",
                data=zip_buffer,
                file_name=zip_filename,
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.info("複数ファイルの場合のみ一括ダウンロードが利用できます")


def create_zip_file(processed_files) -> bytes:
    """処理済みファイルからZIPファイルを作成"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_info in processed_files:
            zip_file.writestr(file_info['name'], file_info['data'])
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


if __name__ == "__main__":
    main()