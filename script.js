/**
 * YouTube リサーチツール
 * フロントエンド JavaScript
 */

console.log("✅ script.js が正常に読み込まれました！");

// ✅ UI要素の取得（nullチェック用に || {}を追加）
const searchButton = document.getElementById("searchButton") || {};
const searchQuery = document.getElementById("searchQuery") || {};
const uploadDate = document.getElementById("uploadDate") || {};
const sortBy = document.getElementById("sortBy") || {};
const videoType = document.getElementById("videoType") || {};
const engagementFilter = document.getElementById("engagementFilter") || {};
const exportButton = document.getElementById("exportButton") || {};
const sheetId = document.getElementById("sheetId") || {};
const scriptUrl = document.getElementById("scriptUrl") || {};
const saveSettingsButton = document.getElementById("saveSettingsButton") || {};
const showSettingsButton = document.getElementById("showSettingsButton") || {};
const setupSection = document.getElementById("setupSection") || {};
const results = document.getElementById("results") || {};
const resultsArea = document.getElementById("resultsArea") || {};
const copyGASButton = document.getElementById("copyGASButton") || {};
const gasCodePreview = document.getElementById("gasCodePreview") || {};
const openScriptEditorBtn = document.getElementById("openScriptEditorBtn") || {};
const oneClickDeployModal = document.getElementById("oneClickDeployModal") || {};
const apiKeyInput = document.getElementById("apiKey") || {};

// ステップナビゲーション要素（nullチェック用に || {}を追加）
const currentStep = document.getElementById("currentStep") || {};
const stepTitle = document.getElementById("stepTitle") || {};
const stepProgress = document.getElementById("stepProgress") || {};
const step1 = document.getElementById("step1") || {};
const step2 = document.getElementById("step2") || {};
const step3 = document.getElementById("step3") || {};
const nextToStep2 = document.getElementById("nextToStep2") || {};
const nextToStep3 = document.getElementById("nextToStep3") || {};
const backToStep1 = document.getElementById("backToStep1") || {};
const backToStep2 = document.getElementById("backToStep2") || {};

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
    // nullチェックを追加して要素が存在する場合のみ処理を実行
    if (gasCodePreview && gasCodePreview.textContent !== undefined) {
        gasCodePreview.textContent = GAS_CODE;
    }
    
    // 保存された設定を読み込む
    loadSettings();
    
    // 設定が完了していればセットアップセクションを非表示
    if (hasValidSettings() && setupSection && setupSection.classList) {
        setupSection.classList.add('hidden');
    }
    
    // ワンクリックデプロイのリンクにクリックイベントを追加
    if (openScriptEditorBtn) {
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
    }
    
    // モーダルを閉じるボタン
    const closeModalButtons = document.querySelectorAll('.closeModal');
    if (closeModalButtons.length > 0) {
        closeModalButtons.forEach(button => {
            button.addEventListener('click', function() {
                if (oneClickDeployModal && oneClickDeployModal.classList) {
                    oneClickDeployModal.classList.add('hidden');
                }
            });
        });
    }
    
    // モーダルの外側をクリックしても閉じる
    if (oneClickDeployModal) {
        oneClickDeployModal.addEventListener('click', function(e) {
            if (e.target === oneClickDeployModal && oneClickDeployModal.classList) {
                oneClickDeployModal.classList.add('hidden');
            }
        });
    }
    
    // ワンクリックデプロイボタンにイベントを追加
    if (copyGASButton) {
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
    }
    
    // ステップナビゲーションのイベント
    if (nextToStep2) {
        nextToStep2.addEventListener('click', function() {
            if (!validateStep1()) return;
            
            showStep(2);
        });
    }
    
    if (nextToStep3) {
        nextToStep3.addEventListener('click', function() {
            showStep(3);
        });
    }
    
    if (backToStep1) {
        backToStep1.addEventListener('click', function() {
            showStep(1);
        });
    }
    
    if (backToStep2) {
        backToStep2.addEventListener('click', function() {
            showStep(2);
        });
    }
    
    // 検索ボタンにイベントリスナーを追加
    if (searchButton) {
        searchButton.addEventListener("click", function () {
            console.log("🔍 検索ボタンがクリックされました");

            if (!hasValidSettings()) {
                alert('先に設定を行なってください');
                if (setupSection && setupSection.classList) {
                    setupSection.classList.remove('hidden');
                }
                showStep(1);
                return;
            }

            if (!searchQuery || !searchQuery.value || !searchQuery.value.trim()) {
                alert("検索キーワードを入力してください");
                return;
            }
            
            // 結果をリセット
            if (results) results.innerHTML = "";
            allVideos = [];
            nextPageToken = "";
            if (resultsArea && resultsArea.classList) {
                resultsArea.classList.add("hidden");
            }
            
            // 検索を実行
            performSearch();
        });
    }
    
    // エクスポートボタンにイベントリスナーを追加
    if (exportButton) {
        exportButton.addEventListener("click", function () {
            console.log("📥 検索結果を Google スプレッドシートに送信...");
            
            if (!hasValidSettings()) {
                alert('先に設定を行なってください');
                if (setupSection && setupSection.classList) {
                    setupSection.classList.remove('hidden');
                }
                showStep(1);
                return;
            }

            if (allVideos.length === 0) {
                alert("検索結果がありません。先に検索を実行してください。");
                return;
            }
            
            // 保存されたスプレッドシートIDを取得
            const savedSheetId = localStorage.getItem('youtubeResearchSheetId');
            
            // エクスポート用のデータを作成
            const exportData = allVideos.map(video => ({
                title: video.title,
                channel: video.channelTitle,
                views: video.viewCount,
                subs: video.subscriberCount,
                url: video.url,
                thumbnail: video.thumbnail,
                duration: video.durationFormatted,
                publishedAt: formatDate(video.publishedAt),
                searchQuery: searchQuery.value.trim()
            }));
            
            // エクスポート中の表示
            exportButton.disabled = true;
            exportButton.innerHTML = '<div class="inline-block animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>送信中...';

            // GASにデータを送信 - CORS回避のためにno-corsモードを使用
            fetch(GOOGLE_SCRIPT_URL, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json"
                },
                mode: "no-cors", // CORSエラーを回避するためにno-corsモードを使用
                body: JSON.stringify({ 
                    sheetId: savedSheetId,
                    searchQuery: searchQuery.value.trim(),
                    videos: exportData
                })
            })
            .then(response => {
                // no-corsモードではレスポンスの内容にアクセスできないため、
                // 成功したと仮定してユーザーに通知
                console.log("📤 リクエスト送信完了");
                alert("Google スプレッドシートに送信しました！");
            })
            .catch((error) => {
                console.error("🚨 スプレッドシート送信エラー:", error);
                alert(`スプレッドシートへの送信に失敗しました: ${error.message}`);
            })
            .finally(() => {
                // ボタンを元に戻す
                exportButton.disabled = false;
                exportButton.innerHTML = '<i class="fas fa-file-export mr-2"></i>スプレッドシートに保存';
            });
        });
    }
    
    // 設定を表示ボタンにイベントリスナーを追加
    if (showSettingsButton) {
        showSettingsButton.addEventListener('click', function() {
            if (setupSection && setupSection.classList) {
                setupSection.classList.remove('hidden');
            }
            showStep(1); // 設定を開いたら最初のステップから表示
        });
    }
    
    // 設定を保存ボタンにイベントリスナーを追加
    if (saveSettingsButton) {
        saveSettingsButton.addEventListener('click', function() {
            if (!scriptUrl || !scriptUrl.value) {
                alert('スクリプトURLを入力してください');
                if (scriptUrl && scriptUrl.focus) scriptUrl.focus();
                return;
            }
            
            if (!sheetId || !sheetId.value) {
                alert('スプレッドシートIDを入力してください');
                if (sheetId && sheetId.focus) sheetId.focus();
                return;
            }
            
            if (!apiKeyInput || !apiKeyInput.value) {
                alert('YouTube Data API キーを入力してください');
                if (apiKeyInput && apiKeyInput.focus) apiKeyInput.focus();
                return;
            }
            
            const scriptUrlValue = scriptUrl.value.trim();
            const sheetIdValue = sheetId.value.trim();
            const apiKeyValue = apiKeyInput.value.trim();
            
            // ローカルストレージに保存
            localStorage.setItem('youtubeResearchScriptUrl', scriptUrlValue);
            localStorage.setItem('youtubeResearchSheetId', sheetIdValue);
            localStorage.setItem('youtubeResearchApiKey', apiKeyValue);
            GOOGLE_SCRIPT_URL = scriptUrlValue;
            
            alert('設定を保存しました！これでツールを使用できます。');
            if (setupSection && setupSection.classList) {
                setupSection.classList.add('hidden');
            }
        });
    }
});

// ステップを表示する関数
function showStep(stepNumber) {
    // すべてのステップを非表示
    const steps = [step1, step2, step3];
    steps.forEach(step => {
        if (step && step.classList) {
            step.classList.add('hidden');
        }
    });
    
    // 指定されたステップを表示
    if (stepNumber === 1) {
        if (step1 && step1.classList) step1.classList.remove('hidden');
        if (currentStep) currentStep.textContent = '1';
        if (stepTitle) stepTitle.textContent = 'スプレッドシートを準備';
        if (stepProgress && stepProgress.style) stepProgress.style.width = '33%';
    } else if (stepNumber === 2) {
        if (step2 && step2.classList) step2.classList.remove('hidden');
        if (currentStep) currentStep.textContent = '2';
        if (stepTitle) stepTitle.textContent = 'Google Apps Scriptを設定';
        if (stepProgress && stepProgress.style) stepProgress.style.width = '66%';
    } else if (stepNumber === 3) {
        if (step3 && step3.classList) step3.classList.remove('hidden');
        if (currentStep) currentStep.textContent = '3';
        if (stepTitle) stepTitle.textContent = 'スクリプトをデプロイ';
        if (stepProgress && stepProgress.style) stepProgress.style.width = '100%';
    }
}

// ステップ1の入力を検証
function validateStep1() {
    if (!sheetId || !sheetId.value) {
        alert('スプレッドシートIDを入力してください');
        if (sheetId && sheetId.focus) sheetId.focus();
        return false;
    }
    
    if (!apiKeyInput || !apiKeyInput.value) {
        alert('YouTube Data API キーを入力してください');
        if (apiKeyInput && apiKeyInput.focus) apiKeyInput.focus();
        return false;
    }
    
    const sheetIdValue = sheetId.value.trim();
    const apiKeyValue = apiKeyInput.value.trim();
    
    if (!sheetIdValue) {
        alert('スプレッドシートIDを入力してください');
        if (sheetId && sheetId.focus) sheetId.focus();
        return false;
    }
    
    if (!apiKeyValue) {
        alert('YouTube Data API キーを入力してください');
        if (apiKeyInput && apiKeyInput.focus) apiKeyInput.focus();
        return false;
    }
    
    return true;
}

// ✅ 設定の読み込み
function loadSettings() {
    const savedScriptUrl = localStorage.getItem('youtubeResearchScriptUrl');
    const savedSheetId = localStorage.getItem('youtubeResearchSheetId');
    const savedApiKey = localStorage.getItem('youtubeResearchApiKey');
    
    if (savedScriptUrl) {
        if (scriptUrl) scriptUrl.value = savedScriptUrl;
        GOOGLE_SCRIPT_URL = savedScriptUrl;
    }
    
    if (savedSheetId && sheetId) {
        sheetId.value = savedSheetId;
    }
    
    if (savedApiKey && apiKeyInput) {
        apiKeyInput.value = savedApiKey;
    }
}

// ✅ 設定が有効かチェック
function hasValidSettings() {
    return localStorage.getItem('youtubeResearchScriptUrl') && 
           localStorage.getItem('youtubeResearchSheetId') &&
           localStorage.getItem('youtubeResearchApiKey');
}

// ✅ YouTube API を使って検索
function performSearch(isLoadMore = false) {
    console.log("📡 YouTube API へのリクエスト開始...");
    
    // 検索中表示を追加
    if (!isLoadMore && results) {
        results.innerHTML = '<div class="col-span-full text-center"><div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-red-600"></div><p class="mt-2">検索中...</p></div>';
    }

    // APIキーを取得
    const apiKey = localStorage.getItem('youtubeResearchApiKey');
    if (!apiKey) {
        alert('YouTube Data API キーが設定されていません。設定画面から入力してください。');
        if (setupSection && setupSection.classList) {
            setupSection.classList.remove('hidden');
        }
        showStep(1);
        return;
    }

    // 基本的なクエリパラメータを設定
    let query = encodeURIComponent(searchQuery.value);
    let apiUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q=${query}&type=video&key=${apiKey}`;
    
    // 並び順を追加
    if (sortBy && sortBy.value) {
        apiUrl += `&order=${sortBy.value}`;
    }
    
    // ページトークンがあれば追加
    if (nextPageToken && isLoadMore) {
        apiUrl += `&pageToken=${nextPageToken}`;
    }
    
    // アップロード日フィルターを追加
    if (uploadDate && uploadDate.value !== "any") {
        const now = new Date();
        let publishedAfter = new Date();
        
        switch(uploadDate.value) {
            case "week":
                publishedAfter.setDate(now.getDate() - 7);
                break;
            case "month":
                publishedAfter.setMonth(now.getMonth() - 1);
                break;
            case "quarter":
                publishedAfter.setMonth(now.getMonth() - 3);
                break;
            case "halfYear":
                publishedAfter.setMonth(now.getMonth() - 6);
                break;
            case "year":
                publishedAfter.setFullYear(now.getFullYear() - 1);
                break;
        }
        
        apiUrl += `&publishedAfter=${publishedAfter.toISOString()}`;
    }

    // YouTube APIを呼び出し
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`APIエラー: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("✅ YouTube API からデータを取得:", data);
            
            if (!data.items || data.items.length === 0) {
                if (results) {
                    results.innerHTML = '<div class="col-span-full text-center text-gray-500">検索結果が見つかりませんでした</div>';
                }
                return;
            }
            
            // 次ページのトークンを保存
            nextPageToken = data.nextPageToken || "";
            
            // 動画IDを抽出
            const videoIds = data.items.map(item => item.id.videoId).join(',');
            
            // 動画の詳細情報を取得
            return fetch(`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${videoIds}&key=${apiKey}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`動画詳細取得エラー: ${response.status}`);
                    }
                    return response.json();
                })
                .then(videoDetails => {
                    // チャンネルIDを抽出
                    const channelIds = [...new Set(videoDetails.items.map(item => item.snippet.channelId))];
                    
                    // チャンネル情報を取得
                    return fetch(`https://www.googleapis.com/youtube/v3/channels?part=statistics&id=${channelIds.join(',')}&key=${apiKey}`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`チャンネル情報取得エラー: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(channelDetails => {
                            // 動画情報を処理
                            if (!isLoadMore && results) {
                                results.innerHTML = "";
                            }
                            
                            // 全ての情報を組み合わせて表示用データを作成
                            const processedVideos = processVideoData(videoDetails.items, channelDetails.items);
                            allVideos = [...allVideos, ...processedVideos];
                            
                            // 結果を表示
                            displayResults(processedVideos);
                            if (resultsArea && resultsArea.classList) {
                                resultsArea.classList.remove("hidden");
                            }
                        });
                });
        })
        .catch(error => {
            console.error("🚨 API Error:", error);
            if (results) {
                results.innerHTML = `<div class="col-span-full text-center text-red-500">エラーが発生しました: ${error.message}</div>`;
            }
        });
}

// 動画データを処理する関数
function processVideoData(videos, channels) {
    const processedVideos = [];
    
    videos.forEach(video => {
        // 動画の長さを取得（PT1H30M15Sの形式）
        const duration = video.contentDetails.duration;
        const durationInSec = parseDuration(duration);
        
        // 短い動画か長い動画かをフィルタリング
        if (videoType && videoType.value === "short" && durationInSec >= 60) {
            return;
        }
        if (videoType && videoType.value === "long" && durationInSec < 60) {
            return;
        }
        
        // 対応するチャンネル情報を取得
        const channelId = video.snippet.channelId;
        const channel = channels.find(ch => ch.id === channelId);
        
        if (!channel) {
            console.warn(`チャンネル情報が見つかりません: ${channelId}`);
            return;
        }
        
        const subscriberCount = parseInt(channel.statistics.subscriberCount || "0");
        const viewCount = parseInt(video.statistics.viewCount || "0");
        
        // エンゲージメントフィルターが有効の場合、1.5倍以上の動画のみ表示
        if (engagementFilter && engagementFilter.checked && viewCount < subscriberCount * 1.5) {
            return;
        }
        
        // 処理済み動画データを作成
        processedVideos.push({
            id: video.id,
            title: video.snippet.title,
            description: video.snippet.description,
            thumbnail: video.snippet.thumbnails.high.url,
            publishedAt: video.snippet.publishedAt,
            channelId: channelId,
            channelTitle: video.snippet.channelTitle,
            viewCount: viewCount,
            likeCount: parseInt(video.statistics.likeCount || "0"),
            commentCount: parseInt(video.statistics.commentCount || "0"),
            subscriberCount: subscriberCount,
            duration: duration,
            durationFormatted: formatDuration(duration),
            url: `https://www.youtube.com/watch?v=${video.id}`
        });
    });
    
    return processedVideos;
}

// ✅ 検索結果を画面に表示
function displayResults(videos) {
    if (!videos || videos.length === 0) {
        if (results && results.innerHTML === "") {
            results.innerHTML = '<div class="col-span-full text-center text-gray-500">条件に一致する動画が見つかりませんでした</div>';
        }
        return;
    }
    
    if (!results) return;
    
    videos.forEach(video => {
        const engagementRatio = (video.viewCount / video.subscriberCount).toFixed(2);
        const isHighEngagement = video.viewCount > video.subscriberCount * 1.5;
        
        const videoElement = document.createElement('div');
        videoElement.className = "bg-white rounded-lg shadow-md overflow-hidden";
        videoElement.innerHTML = `
            <div class="relative">
                <a href="${video.url}" target="_blank">
                    <img src="${video.thumbnail}" alt="${video.title}" class="w-full">
                    <div class="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white text-xs px-1 rounded">
                        ${video.durationFormatted}
                    </div>
                </a>
            </div>
            <div class="p-4">
                <h3 class="font-bold text-gray-800 mb-2 line-clamp-2" title="${video.title}">${video.title}</h3>
                <div class="flex justify-between mb-2">
                    <p class="text-gray-600 text-sm">${video.channelTitle}</p>
                    <p class="text-gray-600 text-sm">${formatNumber(video.subscriberCount)}登録</p>
                </div>
                <div class="flex justify-between text-xs text-gray-500 mb-2">
                    <span>${formatDate(video.publishedAt)}</span>
                    <span>${formatNumber(video.viewCount)}回視聴</span>
                </div>
                <div class="flex justify-between items-center">
                    <a href="${video.url}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm">
                        動画を見る
                    </a>
                    <div class="text-xs ${isHighEngagement ? 'text-green-600 font-bold' : 'text-gray-500'}">
                        エンゲージメント率: ${engagementRatio}x
                    </div>
                </div>
            </div>
        `;
        
        results.appendChild(videoElement);
    });
}

// ユーティリティ関数
function parseDuration(duration) {
    // ISO 8601 形式の期間（PT1H30M15S）をパースして秒数に変換
    const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
    if (!match) return 0;
    
    const hours = parseInt(match[1] || 0);
    const minutes = parseInt(match[2] || 0);
    const seconds = parseInt(match[3] || 0);
    
    return hours * 3600 + minutes * 60 + seconds;
}

function formatDuration(duration) {
    const seconds = parseDuration(duration);
    
    if (seconds < 60) {
        return `0:${seconds.toString().
