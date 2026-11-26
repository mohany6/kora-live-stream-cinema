@echo off
chcp 65001 >nul
echo Copying Blogger Theme XML to clipboard...
powershell -Command "$text = [System.IO.File]::ReadAllText('%~dp0blogger_theme\kora_pro_blogger_theme.xml', [System.Text.Encoding]::UTF8); Set-Clipboard -Value $text"
echo [SUCCESS] Theme code has been copied to your clipboard!
echo You can now go to Blogger -^> Theme -^> Edit HTML and press Ctrl+V.
pause
