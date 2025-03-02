/**
 * YouTube リサーチツール
 * フロントエンド JavaScript
 */

console.log("✅ script.js が正常に読み込まれました！");

// ✅ YouTube API キー（🔴 ここに実際のAPIキーを入れる）
const API_KEY = "AIzaSyBP62VpqSCqz8MvCW_SkEIwV8B3QmTOuyk"; // 実際のAPIキーに変更してください

// ✅ UI要素の取得
const searchButton = document.getElementById("searchButton");
const searchQuery = document.getElementById("searchQuery");
const uploadDate = document.getElementById("uploadDate");
const sortBy = document.getElementById("sortBy");
const videoType = document.getElementById("videoType");
const engagementFilter = document.getElementById("engagementFilter");
const exportButton = document.getElementById("exportButton");
const sheetId = document.getElementById("sheetId");
const scriptUrl = document.getElementById("scriptUrl");
const saveSettingsButton = document.getElementById("saveSettingsButton");
const showSettingsButton = document.getElementById("showSettingsButton");
const setupSection = document.getElementById("setupSection");
const results = document.getElementById("results");
const resultsArea = document.getElementById("resultsArea");
const copyGASButton = document.getElementById("copyGASButton");
const gasCodePreview = document.getElementById("gasCodePreview");
const openScriptEditorBtn = document.getElementById("openScriptEditorBtn");
const oneClickDeployModal = document.getElementById("oneClickDeployModal");

// ステップナビゲーション要素
const currentStep = document.getElementById("currentStep");
const stepTitle = document.getElementById("stepTitle");
const stepProgress = document.getElementById("stepProgress");
const step1 = document.getElementById("step1");
const step2 = document.getElementById("step2");
const step3 = document.getElementById("step3");
const nextToStep2 = document.getElementById("nextToStep2");
const nextToStep3 = document.getElementById("nextToStep3");
const backToStep1 = document.getElementById("backToStep1");
const backToStep2 = document.getElementById("backToStep2");

// Google Apps Scriptのコード
const GAS_CODE = `/**
 * YouTube リサーチツール用 Google Apps Script
 * デプロイ後、URLをHTMLファイルに設定してください
 */

// HTTPリクエストを処理する関数
function doPost(e) {
  try {
    // POSTデータをパース
    const data = JSON.parse(e.postData.contents);
    const sheetId = data.sheetId; // フロントエンドから送信されたスプレッドシートID
    const searchQuery = data.searchQuery;
    const videos = data.videos;
    
    // スプレッドシートを開く
    let spreadsheet;
    try {
      spreadsheet = SpreadsheetApp.openById(sheetId);
    } catch (error) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        error: "スプレッドシートが見つからないか、アクセス権限がありません。"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 検索クエリを用いたシート名を作成（長すぎる場合は切り詰める）
    const sheetName = (searchQuery.length > 20) 
      ? searchQuery.substring(0, 20) + "..." 
      : searchQuery;
    
    // 既存のシートを取得するか、新しいシートを作成
    let sheet = spreadsheet.getSheetByName(sheetName);
    if (!sheet) {
      sheet = spreadsheet.insertSheet(sheetName);
    }
    
    // ヘッダー行を設定
    const headers = ["タイトル", "チャンネル名", "再生回数", "登録者数", "URL", "サムネイルURL", "動画時間", "公開日", "検索クエリ"];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight("bold");
    
    // データ行を作成
    const rows = videos.map(video => [
      video.title,
      video.channel,
      video.views,
      video.subs,
      video.url,
      video.thumbnail,
      video.duration,
      video.publishedAt,
      video.searchQuery
    ]);
    
    // データを書き込む
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
    
    // 列幅を自動調整
    sheet.autoResizeColumns(1, headers.length);
    
    // 成功レスポンスを返す
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: \`\${rows.length}件のデータがスプレッドシートに保存されました。\`
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    // エラーレスポンスを返す
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// CORSを許可するための設定
function doOptions(e) {
  var headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "1728000"
  };
  
  return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT)
    .setHeaders(headers);
}`;

let nextPageToken = "";
let allVideos = []; // 検索結果を保存する配列
let GOOGLE_SCRIPT_URL = ""; // 保存された設定から読み込む

// ✅ 初期化処理
document.addEventListener('DOMContentLoaded', function() {
    // GASコードをプレビューに表示
    gasCodePreview.textContent = GAS_CODE;
    
    // 保存された設定を読み込む
    loadSettings();
    
    // 設定が完了していればセットアップセクションを非表示
    if (hasValidSettings()) {
        setupSection.classList.add('hidden');
    }
    
    // ワンクリックデプロイのリンクにクリックイベントを追加
    openScriptEditorBtn.addEventListener('click', function() {
        // GASコードをクリップボードにコピー
        navigator.clipboard.writeText(GAS_CODE)
            .then(() => {
                console.log('GASコードがクリップボードにコピーされました');
                alert('GASコードがクリップボードにコピーされました。\n開いたGASエディタに貼り付けてください。');
            })
            .catch(err => {
                console.error('コピーに失敗しました:', err);
                alert('コピーに失敗しました。コードを手動でコピーしてください。');
            });
    });
    
    // モーダルを閉じるボタン
    document.querySelectorAll('.closeModal').forEach(button => {
        button.addEventListener('click', function() {
            oneClickDeployModal.classList.add('hidden');
        });
    });
    
    // モーダルの外側をクリックしても閉じる
    oneClickDeployModal.addEventListener('click', function(e) {
        if (e.target === oneClickDeployModal) {
            oneClickDeployModal.classList.add('hidden');
        }
    });
    
    // ワンクリックデプロイボタンにイベントを追加
    copyGASButton.addEventListener('click', function() {
        // GASコードをクリップボードにコピー
        navigator.clipboard.writeText(GAS_CODE)
            .then(() => {
                console.log('GASコードがクリップボードにコピーされました');
                alert('GASコードがクリップボードにコピーされました。');
            })
            .catch(err => {
                console.error('コピーに失敗しました:', err);
                alert('コピーに失敗しました。手動でコードをコピーしてください。');
            });
    });
    
    // ステップナビゲーションのイベント
    nextToStep2.addEventListener('click', function() {
        if (!validateStep1()) return;
        
        showStep(2);
    });
    
    nextToStep3.addEventListener('click', function() {
        showStep(3);
    });
    
    backToStep1.addEventListener('click', function() {
        showStep(1);
    });
    
    backToStep2.addEventListener('click', function() {
        showStep(2);
    });
});

// ステップを表示する関数
function showStep(stepNumber) {
    // すべてのステップを非表示
    [step1, step2, step3].forEach(step => step.classList.add('hidden'));
    
    // 指定されたステップを表示
    if (stepNumber === 1) {
        step1.classList.remove('hidden');
        currentStep.textContent = '1';
        stepTitle.textContent = 'スプレッドシートを準備';
        stepProgress.style.width = '33%';
    } else if (stepNumber === 2) {
        step2.classList.remove('hidden');
        currentStep.textContent = '2';
        stepTitle.textContent = 'Google Apps Scriptを設定';
        stepProgress.style.width = '66%';
    } else if (stepNumber === 3) {
        step3.classList.remove('hidden');
        currentStep.textContent = '3';
        stepTitle.textContent = 'スクリプトをデプロイ';
        stepProgress.style.width = '100%';
    }
}

// ステップ1の入力を検証
function validateStep1() {
    const sheetIdValue = sheetId.value.trim();
    if (!sheetIdValue) {
        alert('スプレッドシートIDを入力してください');
        sheetId.focus();
        return false;
    }
    return true;
}

// ✅ 設定の読み込み
function loadSettings() {
    const savedScriptUrl = localStorage.getItem('youtubeResearchScriptUrl');
    const savedSheetId = localStorage.getItem('youtubeResearchSheetId');
    
    if (savedScriptUrl) {
        scriptUrl.value = savedScriptUrl;
        GOOGLE_SCRIPT_URL = savedScriptUrl;
    }
    
    if (savedSheetId) {
        sheetId.value = savedSheetId;
    }
}

// ✅ 設定が有効かチェック
function hasValidSettings() {
    return localStorage.getItem('youtubeResearchScriptUrl') && 
           localStorage.getItem('youtubeResearchSheetId');
}

// ✅ 設定を保存
saveSettingsButton.addEventListener('click', function() {
    const scriptUrlValue = scriptUrl.value.trim();
    const sheetIdValue = sheetId.value.trim();
    
    if (!scriptUrlValue) {
        alert('スクリプトURLを入力してください');
        scriptUrl.focus();
        return;
    }
    
    if (!sheetIdValue) {
        alert('スプレッドシートIDを入力してください');
        sheetId.focus();
        return;
    }
    
    // ローカルストレージに保存
    localStorage.setItem('youtubeResearchScriptUrl', scriptUrlValue);
    localStorage.setItem('youtubeResearchSheetId', sheetIdValue);
    GOOGLE_SCRIPT_URL = scriptUrlValue;
    
    alert('設定を保存しました！これでツールを使用できます。');
    setupSection.classList.add('hidden');
