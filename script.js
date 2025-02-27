/**
 * YouTube リサーチツール
 * フロントエンド JavaScript
 */

console.log("✅ script.js が正常に読み込まれました！");

// デフォルトのGoogle Apps Script URL
const DEFAULT_GAS_URL = "https://script.google.com/macros/s/AKfycbyt8hOMKsvlm79dWGYbLYH0thLHddtrYYuuDgqZb_Rcgm5OMt0tVd1KOOgc-SlARP6t/exec";

// UI要素の取得
const apiKeyInput = document.getElementById("apiKey");
const spreadsheetIdInput = document.getElementById("spreadsheetId");
const gasUrlInput = document.getElementById("gasUrl");
const saveSettingsButton = document.getElementById("saveSettings");
const searchButton = document.getElementById("searchButton");
const searchQuery = document.getElementById("searchQuery");
const uploadDate = document.getElementById("uploadDate");
const sortBy = document.getElementById("sortBy");
const videoType = document.getElementById("videoType");
const engagementFilter = document.getElementById("engagementFilter");
const exportButton = document.getElementById("exportButton");
const results = document.getElementById("results");
const resultsArea = document.getElementById("resultsArea");

let nextPageToken = "";
let allVideos = []; // 検索結果を保存する配列

// APIキーの管理
let API_KEY = ""; // 初期値は空

// ローカルストレージからAPIキーを取得
if (localStorage.getItem("youtube_api_key")) {
    apiKeyInput.value = localStorage.getItem("youtube_api_key");
    API_KEY = apiKeyInput.value;
}

// APIキー入力時の処理
apiKeyInput.addEventListener("change", function() {
    API_KEY = apiKeyInput.value.trim();
    localStorage.setItem("youtube_api_key", API_KEY);
});

// スプレッドシート関連の設定
let SPREADSHEET_ID = localStorage.getItem("spreadsheet_id") || "";
let GAS_URL = localStorage.getItem("gas_url") || DEFAULT_GAS_URL;

// 保存された設定を表示
if (spreadsheetIdInput) spreadsheetIdInput.value = SPREADSHEET_ID;
if (gasUrlInput) gasUrlInput.value = GAS_URL;

// 設定保存ボタンのイベント
if (saveSettingsButton) {
    saveSettingsButton.addEventListener("click", function() {
        SPREADSHEET_ID = spreadsheetIdInput.value.trim();
        GAS_URL = gasUrlInput.value.trim() || DEFAULT_GAS_URL;
        
        localStorage.setItem("spreadsheet_id", SPREADSHEET_ID);
        localStorage.setItem("gas_url", GAS_URL);
        
        alert("設定を保存しました");
    });
}

// 検索ボタンのクリックイベント
searchButton.addEventListener("click", function () {
    console.log("🔍 検索ボタンがクリックされました");

    if (!searchQuery.value.trim()) {
        alert("検索キーワードを入力してください");
        return;
    }
    
    if (!API_KEY) {
        alert("YouTube Data APIキーを入力してください");
        return;
    }
    
    // 結果をリセット
    results.innerHTML = "";
    allVideos = [];
    nextPageToken = "";
    resultsArea.classList.add("hidden");
    
    // 検索を実行
    performSearch();
});

// YouTube API を使って検索
function performSearch(isLoadMore = false) {
    console.log("📡 YouTube API へのリクエスト開始...");
    
    // 検索中表示を追加
    if (!isLoadMore) {
        results.innerHTML = '<div class="col-span-full text-center"><div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-red-600"></div><p class="mt-2">検索中...</p></div>';
    }

    // 基本的なクエリパラメータを設定
    let query = encodeURIComponent(searchQuery.value);
    let apiUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q=${query}&type=video&key=${API_KEY}`;
    
    // 並び順を追加
    apiUrl += `&order=${sortBy.value}`;
    
    // ページトークンがあれば追加
    if (nextPageToken && isLoadMore) {
        apiUrl += `&pageToken=${nextPageToken}`;
    }
    
    // アップロード日フィルターを追加
    if (uploadDate.value !== "any") {
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
                results.innerHTML = '<div class="col-span-full text-center text-gray-500">検索結果が見つかりませんでした</div>';
                return;
            }
            
            // 次ページのトークンを保存
            nextPageToken = data.nextPageToken || "";
            
            // 動画IDを抽出
            const videoIds = data.items.map(item => item.id.videoId).join(',');
            
            // 動画の詳細情報を取得
            return fetch(`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${videoIds}&key=${API_KEY}`)
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
                    return fetch(`https://www.googleapis.com/youtube/v3/channels?part=statistics&id=${channelIds.join(',')}&key=${API_KEY}`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`チャンネル情報取得エラー: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(channelDetails => {
                            // 動画情報を処理
                            if (!isLoadMore) {
                                results.innerHTML = "";
                            }
                            
                            // 全ての情報を組み合わせて表示用データを作成
                            const processedVideos = processVideoData(videoDetails.items, channelDetails.items);
                            allVideos = [...allVideos, ...processedVideos];
                            
                            // 結果を表示
                            displayResults(processedVideos);
                            resultsArea.classList.remove("hidden");
                        });
                });
        })
        .catch(error => {
            console.error("🚨 API Error:", error);
            results.innerHTML = `<div class="col-span-full text-center text-red-500">エラーが発生しました: ${error.message}</div>`;
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
        // 60秒以下をショート動画とする
        if (videoType.value === "short" && durationInSec > 60) {
            return;
        }
        if (videoType.value === "long" && durationInSec <= 60) {
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
        if (engagementFilter.checked && viewCount < subscriberCount * 1.5) {
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

// 検索結果を画面に表示
function displayResults(videos) {
    if (!videos || videos.length === 0) {
        if (results.innerHTML === "") {
            results.innerHTML = '<div class="col-span-full text-center text-gray-500">条件に一致する動画が見つかりませんでした</div>';
        }
        return;
    }
    
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

// 検索結果を Google スプレッドシートに送信（エクスポート時のみ）
exportButton.addEventListener("click", function () {
    console.log("📥 検索結果を Google スプレッドシートに送信...");

    if (allVideos.length === 0) {
        alert("検索結果がありません。");
        return;
    }
    
    // スプレッドシートIDのチェック
    if (!SPREADSHEET_ID) {
        alert("スプレッドシートIDが設定されていません。エクスポート設定でスプレッドシートIDを入力してください。");
        return;
    }
    
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

    // リクエストデータを作成
    const requestData = { 
        searchQuery: searchQuery.value.trim(),
        videos: exportData,
        spreadsheetId: SPREADSHEET_ID
    };

    // GASにデータを送信 - CORS回避のためにno-corsモードを使用
    fetch(GAS_URL, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json"
        },
        mode: "no-cors", // CORSエラーを回避するためにno-corsモードを使用
        body: JSON.stringify(requestData)
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
        exportButton.innerHTML = '検索結果をエクスポート';
    });
});

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
        return `0:${seconds.toString().padStart(2, '0')}`;
    }
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes < 60) {
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toString();
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP');
}
