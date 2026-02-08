
const BASE_URL = "http://127.0.0.1:8000";   // <-- change if your Python backend runs on another port
// admin.js
document.addEventListener('DOMContentLoaded', function() {
    // confirm delete forms
    const forms = document.querySelectorAll('.delete-user-form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const name = form.getAttribute('data-user-name') || 'this user';
            if (confirm(`Are you sure you want to delete ${name}? This cannot be undone.`)) {
                form.submit();
            }
        });
    });
});

// -----------------------------
//  Fetch all news
// -----------------------------
async function loadNews() {
    try {
        let response = await fetch(`${BASE_URL}/news/all`);
        let data = await response.json();

        let container = document.getElementById("newsList");
        container.innerHTML = "";

        data.forEach(item => {
            container.innerHTML += `
                <div class="news-card">
                    <h3>${item.title}</h3>
                    <p>${item.description}</p>
                    <button onclick="deleteNews('${item.id}')">Delete</button>
                    <button onclick="editNews('${item.id}', '${item.title}', '${item.description}')">Edit</button>
                </div>
            `;
        });

    } catch (error) {
        console.error("Error fetching news:", error);
        alert("Failed to load news from server.");
    }
}

// -----------------------------
//  Add news
// -----------------------------
async function addNews() {
    let title = document.getElementById("title").value;
    let description = document.getElementById("description").value;

    if (!title || !description) {
        alert("Please fill all fields");
        return;
    }

    try {
        await fetch(`${BASE_URL}/news/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                description: description
            })
        });

        alert("News added successfully!");
        loadNews();

    } catch (error) {
        alert("Error adding news!");
        console.log(error);
    }
}

// -----------------------------
//  Delete news
// -----------------------------
async function deleteNews(id) {
    try {
        await fetch(`${BASE_URL}/news/delete/${id}`, {
            method: "DELETE"
        });

        alert("News deleted successfully!");
        loadNews();

    } catch (error) {
        alert("Error deleting news!");
    }
}

// -----------------------------
//  Edit News (shows popup)
// -----------------------------
function editNews(id, title, desc) {
    document.getElementById("editId").value = id;
    document.getElementById("editTitle").value = title;
    document.getElementById("editDescription").value = desc;

    document.getElementById("editPopup").style.display = "block";
}

// -----------------------------
//  Save edited news
// -----------------------------
async function updateNews() {
    let id = document.getElementById("editId").value;
    let title = document.getElementById("editTitle").value;
    let description = document.getElementById("editDescription").value;

    try {
        await fetch(`${BASE_URL}/news/update/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                description: description
            })
        });

        alert("News updated successfully!");
        document.getElementById("editPopup").style.display = "none";
        loadNews();

    } catch (error) {
        alert("Error updating news!");
    }
}

// -----------------------------
//  Close popup
// -----------------------------
function closePopup() {
    document.getElementById("editPopup").style.display = "none";
}

// Load news when page opens
window.onload = loadNews;
