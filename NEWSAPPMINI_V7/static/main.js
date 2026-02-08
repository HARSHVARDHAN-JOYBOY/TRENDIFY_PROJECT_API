// static/main.js (User-facing features)
const searchBtn = document.getElementById("searchBtn");
const topicInput = document.getElementById("topic");
const sortSelect = document.getElementById("sort");
const newsContainer = document.getElementById("newsContainer");
const loader = document.getElementById("loader");

// ========================= NEWS SEARCH ==============================

async function getNews() {
  const topic = topicInput.value.trim();
  const sort = sortSelect.value;
  const isLoggedIn = document.body.dataset.loggedIn === 'true';

  if (!isLoggedIn) {
      alert("Please login to search for news.");
      return;
  }
  if (!topic) {
    alert("Please enter a topic.");
    return;
  }

  loader.style.display = "block";
  newsContainer.innerHTML = "";

  try {
    const res = await fetch(`/api/news?topic=${encodeURIComponent(topic)}&sort=${sort}`);
    const data = await res.json();

    loader.style.display = "none";

    if (!res.ok) {
      newsContainer.innerHTML = `<p class="card" style="color: red;">Error: ${data.error}</p>`;
      return;
    }

    if (data.length === 0) {
        newsContainer.innerHTML = `<p class="card">No articles found for that topic.</p>`;
        return;
    }

    data.forEach((a, i) => {
      const item = document.createElement("div");
      item.className = "news-item card";

      item.innerHTML = `
        <div>
          <h3>${i + 1}. ${a.title}</h3>
          <p>Source: ${a.source}</p>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <button class="save-btn" 
              data-title="${encodeURIComponent(a.title)}" 
              data-url="${encodeURIComponent(a.url)}"
              data-source="${encodeURIComponent(a.source)}"
              data-published-at="${a.published_at}">
              💾 Save
          </button>
          <a href="${a.url}" target="_blank">Read →</a>
        </div>
      `;
      newsContainer.appendChild(item);
    });

    document.querySelectorAll('.save-btn').forEach(btn => {
        btn.addEventListener('click', saveArticle);
    });

  } catch (err) {
    loader.style.display = "none";
    newsContainer.innerHTML = `<p class="card" style="color: red;">Error: ${err.message}</p>`;
  }
}


// ========================= SAVE ARTICLE ==============================

async function saveArticle(event) {
    const btn = event.target;
    const articleData = {
        title: decodeURIComponent(btn.dataset.title),
        url: decodeURIComponent(btn.dataset.url),
        source: decodeURIComponent(btn.dataset.source),
        published_at: btn.dataset.publishedAt,
    };

    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const response = await fetch('/api/save_article', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(articleData),
        });

        const data = await response.json();

        if (data.status === 'success') {
            btn.textContent = 'Saved! ✅';
        } else if (data.status === 'warning') {
            btn.textContent = 'Already Saved!';
        } else {
            btn.textContent = 'Failed ❌';
            alert(`Error: ${data.message}`);
        }

    } catch (error) {
        btn.textContent = 'Error ❌';
        alert("Network error while saving.");
    }

    setTimeout(() => {
        btn.disabled = false;
        if (btn.textContent.includes('Saved')) {
            btn.textContent = 'Saved! ✅';
        } else {
            btn.textContent = '💾 Save';
        }
    }, 2000);
}


// ========================= VIDEO SEARCH (NEW) ==============================

const videoBtn = document.getElementById("videoSearchBtn");
const videoInput = document.getElementById("videoTopic");
const videoContainer = document.getElementById("videoContainer");

async function getVideos() {
    const q = videoInput.value.trim();
    const isLoggedIn = document.body.dataset.loggedIn === 'true';

    if (!isLoggedIn) {
        alert("Please login to search for videos.");
        return;
    }

    if (!q) {
        alert("Enter a video search keyword.");
        return;
    }

    videoContainer.innerHTML = "<p>Loading videos...</p>";

    try {
        const res = await fetch(`/api/videos?topic=${encodeURIComponent(q)}`);
        const data = await res.json();

        if (data.error) {
            videoContainer.innerHTML = `<p style="color:red;">${data.error}</p>`;
            return;
        }

        if (data.length === 0) {
            videoContainer.innerHTML = `<p>No videos found.</p>`;
            return;
        }

        videoContainer.innerHTML = data
            .map(v => `
                <div class="card">
                    <img src="${v.thumbnail}" class="thumb">
                    <h3>${v.title}</h3>
                    <p>${v.channel}</p>
                    <a href="${v.url}" target="_blank" class="btn">Watch Video</a>
                </div>
            `)
            .join("");

    } catch (e) {
        videoContainer.innerHTML = `<p style="color:red;">Error loading videos.</p>`;
    }
}


// ========================= EVENT LISTENERS ==============================

if (searchBtn) searchBtn.onclick = getNews;

if (topicInput) {
  topicInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") getNews();
  });
}

// Video search events
if (videoBtn) videoBtn.onclick = getVideos;

if (videoInput) {
    videoInput.addEventListener("keyup", (e) => {
        if (e.key === "Enter") getVideos();
    });
}
