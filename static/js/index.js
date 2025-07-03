const fetchBtn = document.getElementById("fetchSchedule");
const container = document.getElementById("schedule-container");
const runBtn = document.getElementById("run-btn");
const loading = document.getElementById("loadingOverlay");
const dateDropdown = document.getElementById("dateDropdown");

function showLoading() {
  loading.classList.remove("d-none");
}
function hideLoading() {
  loading.classList.add("d-none");
}

fetchBtn.addEventListener("click", async () => {
  const date  = document.getElementById("dateDropdown").value;
  const time  = document.getElementById("time").value;
  const from  = document.getElementById("fromStation").value;
  const to    = document.getElementById("toStation").value;

  if (!date || !time || !from || !to) {
    return alert("날짜·시간·출발역·도착역 모두 선택해주세요.");
  }

  const params = new URLSearchParams({
    date,
    time,
    from_station: from,
    to_station: to
  });

  showLoading();
  try {
    const res = await fetch(`/schedule?${params.toString()}`, {
      method: 'GET'
    });
    if (!res.ok) throw new Error(res.statusText);

    const data = await res.json();
    renderSchedule(data);

    const container = document.getElementById("schedule-container");
    container.scrollIntoView({ behavior: "smooth", block: "center" });

  } catch (err) {
    alert('스케줄 조회 중 오류: ' + err.message);
  } finally {
    hideLoading();  // ← 항상 로딩 숨김
  }
});

// 좌석 고르기 렌더링
function renderSchedule(data) {
  container.innerHTML = "";
  const table = document.createElement("table");
  table.className = "table table-bordered text-center";

  table.innerHTML = `
    <thead class="table-light">
      <tr>
        <th>열차번호</th><th>출발시간</th><th>도착시간</th><th>예약상태</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement("tbody");
  data.forEach(item => {
    const tr = document.createElement("tr");

    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.name = "seats";
    chk.value = item.train;
    chk.style.display = "none";

    const tdTrain = document.createElement("td");
    tdTrain.appendChild(chk);
    tdTrain.appendChild(document.createTextNode(item.train));
    tr.appendChild(tdTrain);

    ["depart","arrive"].forEach(key => {
      const td = document.createElement("td");
      td.innerText = item[key];
      tr.appendChild(td);
    });

    const tdStatus = document.createElement("td");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.innerText = item.status;
    btn.className = "btn btn-sm " +
      (item.status==="매진" ? "btn-secondary" : "btn-success");
    tdStatus.appendChild(btn);
    tr.appendChild(tdStatus);

    tr.addEventListener("click", () => {
      chk.checked = !chk.checked;
      tr.classList.toggle("table-primary", chk.checked);

      const any = Array.from(container.querySelectorAll('input[name="seats"]'))
                       .some(c=>c.checked);

      if (any) {
        runBtn.disabled = false;
      } 
      else {
        runBtn.disabled = true;
      }
    });

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
}

// 오늘 기준 한달 렌더링
function populateDateDropdown() {
  const today = new Date();
  for (let i = 0; i <= 30; i++) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const val = `${yyyy}${mm}${dd}`;
    const text = `${yyyy}/${mm}/${dd}(${['일','월','화','수','목','금','토'][d.getDay()]})`;

    const opt = document.createElement('option');
    opt.value = val;
    opt.innerText = text;
    dateDropdown.appendChild(opt);
  }
}
populateDateDropdown();

 // run 호출
document.getElementById('run-btn').addEventListener('click', runMacro);

async function runMacro() {
  const login_id = document.getElementById('loginField').value;
  const login_psw = document.getElementById('pwField').value;
  const from_stn = document.getElementById('fromStation').value;
  const to_stn = document.getElementById('toStation').value;
  const date = document.getElementById('dateDropdown').value;
  const time = document.getElementById('time').value;
  const reserve = document.getElementById('reserveSwitch').checked;
  const seatsEls = Array.from(document.querySelectorAll('input[name="seats"]:checked'));
  const allSeats = Array.from(document.querySelectorAll('input[name="seats"]'));
  const seats = seatsEls.map(el => allSeats.indexOf(el) + 1);

  if (![login_id, login_psw, from_stn, to_stn, date, time].every(Boolean) || seats.length === 0) {
    return alert('모든 필드를 채우고 열차를 최소 하나 선택하세요.');
  }

  const params = new URLSearchParams();
  params.append('login_id', login_id);
  params.append('login_psw', login_psw);
  params.append('from_station', from_stn);
  params.append('to_station', to_stn);
  params.append('date', date);
  params.append('time', time);
  params.append('reserve', reserve);
  seats.forEach(s => params.append('seats', s));

  try {
    const res = await fetch('/run', {
      method: 'POST',
      body: params
    });
    if (!res.ok) throw new Error(res.statusText);

    const success = await res.json();
    if (success) {
      triggerAlarmPopup({
        title: '🚀 예매 알림',
        messages: [
          '10분 내에 결제하셔야 예매가 확정됩니다.'
        ]
      });
    } else {
      alert('예약에 실패했습니다.');
    }
  } catch (err) {
    alert('매크로 실행 중 오류: ' + err.message);
  }
}

// 알람 모달 + 사운드 재생
function triggerAlarmPopup({ title, messages }) {
  const modalEl = document.getElementById('sirenModal');
  const titleEl = document.getElementById('sirenModalLabel');
  const bodyEl  = document.getElementById('sirenModalBody');
  if (!modalEl || !titleEl || !bodyEl) return;

  titleEl.innerText = title;
  bodyEl.innerHTML = messages.map(msg => `<p>${msg}</p>`).join('');

  const audio = new Audio('/static/siren.mp3');
  audio.loop   = true;
  audio.volume = 1.0;
  audio.play().catch(() => {
    alert('브라우저 자동 재생 정책으로 차단되었습니다.\n설정 변경 후 다시 시도해주세요.');
  });

  const sirenModal = new bootstrap.Modal(modalEl);
  sirenModal.show();

  modalEl.addEventListener('hidden.bs.modal', () => {
    audio.pause();
    audio.currentTime = 0;
  }, { once: true });
}

document.addEventListener('DOMContentLoaded', () => {
  const testBtn = document.getElementById('testSiren');
  if (testBtn) {
    testBtn.addEventListener('click', () => {
      triggerAlarmPopup({
        title: '🛎 싸이렌 테스트',
        messages: [
          '10분 내에 결제하지 않으면 예매가 취소됩니다.',
          '충분히 들을 수 있게 볼륨을 조절해 주세요.'
        ]
      });
    });
  }
});