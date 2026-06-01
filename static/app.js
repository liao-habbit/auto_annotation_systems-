let currentImage = null;
let img = new Image();
let boxes = [];
let selectedBox = -1;

let imgW = 0;
let imgH = 0;
let scale = 1;

let isDrawing = false;
let startX = 0;
let startY = 0;
let tempBox = null;

let dirty = false;
let modified = false;

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

// ======================================================
// Load image
// ======================================================
function selectImage(name) {
    dirty = false;
    modified = false;
    currentImage = name;
    selectedBox = -1;

    document.querySelectorAll(".imageItem").forEach(item => {
        item.classList.remove("activeItem");
        if (item.dataset.name === name) {
            item.classList.add("activeItem");
        }
    });

    fetch(`/load/${name}`)
        .then(r => r.json())
        .then(data => {
            imgW = data.width;
            imgH = data.height;
            boxes = data.boxes;

            img.onload = function () {
                fitImageToWindow();
                draw();
                renderBoxList();
                updateStatus();
            };

            img.src = `/image/${name}?t=${Date.now()}`;
        });
}

// ======================================================
// Fit image to available window
// ======================================================
function fitImageToWindow() {
    const wrap = document.getElementById("canvasWrap");

    const availableW = wrap.clientWidth - 20;
    const availableH = wrap.clientHeight - 20;

    const scaleW = availableW / imgW;
    const scaleH = availableH / imgH;

    scale = Math.min(scaleW, scaleH, 1);

    canvas.width = Math.round(imgW * scale);
    canvas.height = Math.round(imgH * scale);
}

// ======================================================
// Coordinate tools
// ======================================================
function getMousePos(evt) {
    const rect = canvas.getBoundingClientRect();

    return {
        x: Math.round((evt.clientX - rect.left) / scale),
        y: Math.round((evt.clientY - rect.top) / scale)
    };
}

function clampBox(b) {
    b.xmin = Math.max(0, Math.min(imgW - 1, parseInt(b.xmin)));
    b.ymin = Math.max(0, Math.min(imgH - 1, parseInt(b.ymin)));
    b.xmax = Math.max(0, Math.min(imgW - 1, parseInt(b.xmax)));
    b.ymax = Math.max(0, Math.min(imgH - 1, parseInt(b.ymax)));

    if (b.xmax < b.xmin) {
        [b.xmin, b.xmax] = [b.xmax, b.xmin];
    }

    if (b.ymax < b.ymin) {
        [b.ymin, b.ymax] = [b.ymax, b.ymin];
    }

    return b;
}

function defaultNewLabel() {
    if (boxes.length > 0) return boxes[0].label;
    return CLASSES[0];
}

// ======================================================
// Draw canvas
// ======================================================
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    boxes.forEach((b, i) => {
        const x = b.xmin * scale;
        const y = b.ymin * scale;
        const w = (b.xmax - b.xmin) * scale;
        const h = (b.ymax - b.ymin) * scale;

        let color = "red";
        if (b.source === "expert") color = "blue";
        if (b.source === "new") color = "lime";

        ctx.strokeStyle = color;
        ctx.lineWidth = i === selectedBox ? 5 : 3;
        ctx.strokeRect(x, y, w, h);

        ctx.font = "18px Arial";
        ctx.fillStyle = color;

        const txt = `${ZH[b.label]} (${b.label})`;
        ctx.fillText(txt, x, Math.max(22, y - 5));
    });

    if (tempBox) {
        const x = tempBox.xmin * scale;
        const y = tempBox.ymin * scale;
        const w = (tempBox.xmax - tempBox.xmin) * scale;
        const h = (tempBox.ymax - tempBox.ymin) * scale;

        ctx.strokeStyle = "cyan";
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);
    }
}

// ======================================================
// Render right panel
// ======================================================
function renderBoxList() {
    const div = document.getElementById("boxList");
    div.innerHTML = "";

    boxes.forEach((b, i) => {
        let options = "";

        CLASSES.forEach(c => {
            options += `
            <option value="${c}" ${c === b.label ? "selected" : ""}>
            ${ZH[c]} (${c})
            </option>`;
        });

        const selectedClass = i === selectedBox ? " selectedBox" : "";

        div.innerHTML += `
        <div class="boxCard${selectedClass}" id="boxCard_${i}" onclick="selectBox(${i})">
            <b>${i === selectedBox ? "👉 " : ""}Box ${i}</b><br>

            <select
                onmousedown="event.stopPropagation();"
                onclick="event.stopPropagation();"
                onchange="changeLabel(${i}, this.value); event.stopPropagation();">
                ${options}
            </select>

            <br><br>

            xmin <input type="number" value="${b.xmin}"
                onmousedown="event.stopPropagation();"
                onclick="event.stopPropagation();"
                onchange="changeCoord(${i}, 'xmin', this.value); event.stopPropagation();">

            ymin <input type="number" value="${b.ymin}"
                onmousedown="event.stopPropagation();"
                onclick="event.stopPropagation();"
                onchange="changeCoord(${i}, 'ymin', this.value); event.stopPropagation();"><br>

            xmax <input type="number" value="${b.xmax}"
                onmousedown="event.stopPropagation();"
                onclick="event.stopPropagation();"
                onchange="changeCoord(${i}, 'xmax', this.value); event.stopPropagation();">

            ymax <input type="number" value="${b.ymax}"
                onmousedown="event.stopPropagation();"
                onclick="event.stopPropagation();"
                onchange="changeCoord(${i}, 'ymax', this.value); event.stopPropagation();"><br>

            <button onclick="deleteBox(${i}); event.stopPropagation();">Delete</button>
        </div>`;
    });

    draw();

    if (selectedBox >= 0) {
        const selectedCard = document.getElementById(`boxCard_${selectedBox}`);
        if (selectedCard) {
            selectedCard.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        }
    }
}

// ======================================================
// Box operations
// ======================================================
function selectBox(i) {
    selectedBox = i;
    renderBoxList();
    draw();
}

function changeLabel(i, v) {
    boxes[i].label = v;
    boxes[i].source = "expert";
    selectedBox = i;

    dirty = true;
    modified = true;

    draw();
    updateStatus();
}

function changeCoord(i, key, value) {
    boxes[i][key] = parseInt(value);
    boxes[i] = clampBox(boxes[i]);
    boxes[i].source = "expert";
    selectedBox = i;

    dirty = true;
    modified = true;

    draw();
    updateStatus();
}

function deleteBox(i) {
    boxes.splice(i, 1);
    selectedBox = -1;

    dirty = true;
    modified = true;

    draw();
    renderBoxList();
    updateStatus();
}

function findBoxAt(pos) {
    for (let i = boxes.length - 1; i >= 0; i--) {
        const b = boxes[i];

        if (
            pos.x >= b.xmin &&
            pos.x <= b.xmax &&
            pos.y >= b.ymin &&
            pos.y <= b.ymax
        ) {
            return i;
        }
    }

    return -1;
}

// ======================================================
// Mouse drawing new boxes
// ======================================================
canvas.addEventListener("mousedown", function (evt) {
    const pos = getMousePos(evt);
    const hit = findBoxAt(pos);

    if (hit >= 0) {
        selectedBox = hit;
        renderBoxList();
        draw();
        return;
    }

    isDrawing = true;
    startX = pos.x;
    startY = pos.y;

    tempBox = {
        xmin: startX,
        ymin: startY,
        xmax: startX,
        ymax: startY
    };
});

canvas.addEventListener("mousemove", function (evt) {
    if (!isDrawing) return;

    const pos = getMousePos(evt);

    tempBox = clampBox({
        xmin: Math.min(startX, pos.x),
        ymin: Math.min(startY, pos.y),
        xmax: Math.max(startX, pos.x),
        ymax: Math.max(startY, pos.y)
    });

    draw();
});

canvas.addEventListener("mouseup", function () {
    if (!isDrawing) return;

    isDrawing = false;

    if (tempBox) {
        const bw = tempBox.xmax - tempBox.xmin;
        const bh = tempBox.ymax - tempBox.ymin;

        if (bw > 10 && bh > 10) {
            boxes.push({
                label: defaultNewLabel(),
                xmin: tempBox.xmin,
                ymin: tempBox.ymin,
                xmax: tempBox.xmax,
                ymax: tempBox.ymax,
                source: "new"
            });

            selectedBox = boxes.length - 1;
            dirty = true;
            modified = true;
        }
    }

    tempBox = null;

    draw();
    renderBoxList();
    updateStatus();
});

// ======================================================
// Status
// ======================================================
function updateStatus() {
    document.getElementById("status").innerHTML =
        `${currentImage} | ${boxes.length} boxes ${dirty ? "｜尚未儲存" : ""}`;
}

// ======================================================
// Save / Review
// ======================================================
function postSave(isModified, afterSave = null, showAlert = true) {
    fetch("/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            filename: currentImage,
            width: imgW,
            height: imgH,
            boxes: boxes,
            modified: isModified
        })
    })
    .then(r => r.json())
    .then(data => {
        dirty = false;
        modified = isModified;
        markCurrentImageStatus(isModified);
        updateStatus();

        if (showAlert) {
            alert(isModified ? "已儲存修改" : "已標記為審核OK");
        }

        if (afterSave) afterSave();
    });
}

function saveXML() {
    postSave(modified, null, true);
}

function reviewOK() {
    postSave(false, null, true);
}

function reviewOKNext() {
    postSave(false, function () {
        goImage(1);
    }, false);
}

function saveThenGo(direction) {
    postSave(modified, function () {
        goImage(direction);
    }, false);
}

function markCurrentImageStatus(isModified) {
    const items = document.querySelectorAll(".imageItem");

    items.forEach(item => {
        if (item.dataset.name === currentImage) {
            item.classList.remove("reviewedItem");
            item.classList.remove("modifiedItem");

            const span = item.querySelector("span");

            if (isModified) {
                item.classList.add("modifiedItem");
                if (span) {
                    span.innerHTML = "●";
                    span.className = "modified";
                }
            } else {
                item.classList.add("reviewedItem");
                if (span) {
                    span.innerHTML = "✓";
                    span.className = "done";
                }
            }
        }
    });
}

// ======================================================
// Open folders / shutdown
// ======================================================
function openFolder(folder) {
    fetch(`/open_folder/${folder}`)
        .then(r => r.json())
        .then(data => {
            if (data.status !== "ok") {
                alert("無法開啟資料夾");
            }
        });
}

function shutdownApp() {
    const ok = confirm("確定要關閉標註工具嗎？請確認目前圖片已儲存。");
    if (!ok) return;

    fetch("/shutdown", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            alert("程式已關閉，可以關閉此瀏覽器分頁。");
        });
}

// ======================================================
// Navigation
// ======================================================
function goImage(direction) {
    const items = document.querySelectorAll(".imageItem");

    for (let i = 0; i < items.length; i++) {
        if (items[i].dataset.name === currentImage) {
            const ni = i + direction;

            if (ni >= 0 && ni < items.length) {
                selectImage(items[ni].dataset.name);
            }

            break;
        }
    }
}

function nextImage() {
    if (dirty) {
        const ok = confirm("目前圖片已有修改但尚未儲存，是否先儲存再切換下一張？");

        if (ok) {
            saveThenGo(1);
        } else {
            const discard = confirm("確定不儲存修改並切換下一張嗎？");
            if (discard) goImage(1);
        }
    } else {
        goImage(1);
    }
}

function prevImage() {
    if (dirty) {
        const ok = confirm("目前圖片已有修改但尚未儲存，是否先儲存再切換上一張？");

        if (ok) {
            saveThenGo(-1);
        } else {
            const discard = confirm("確定不儲存修改並切換上一張嗎？");
            if (discard) goImage(-1);
        }
    } else {
        goImage(-1);
    }
}

// ======================================================
// Keyboard shortcuts
// ======================================================
document.addEventListener("keydown", function (e) {
    if (e.key === "Delete") {
        if (selectedBox >= 0) deleteBox(selectedBox);
    }

    if (e.key === "a" || e.key === "A") prevImage();
    if (e.key === "d" || e.key === "D") nextImage();
    if (e.key === "s" || e.key === "S") saveXML();
    if (e.key === "q" || e.key === "Q") reviewOKNext();
});

// ======================================================
// Window resize: refit image
// ======================================================
window.addEventListener("resize", function () {
    if (!currentImage) return;
    fitImageToWindow();
    draw();
});

// ======================================================
// Init
// ======================================================
window.onload = function () {
    const first = document.querySelector(".imageItem");

    if (first) {
        selectImage(first.dataset.name);
    }
};