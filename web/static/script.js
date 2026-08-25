const liste = document.getElementById('liste-offres');
const job_count = document.getElementById('job_count');
const filter_buttons = document.querySelectorAll('.filtre-btn[data-filtre]');
const jobs = document.querySelectorAll('#liste-offres .offre');

let get_job_count = () => {
  let cpt = 0;
  jobs.forEach(job => {
    if (job.style.display !== 'none') cpt += 1;
  });
  return cpt;
};
job_count.innerHTML = get_job_count();

function markAsSeen(offreEl) {
  if (offreEl.dataset.vu === 'False') {
    offreEl.dataset.vu = 'True';
    offreEl.classList.add('etat-vu');
    const btnMarkAsUnseen = offreEl.querySelector('.btn-mark-as-unseen');
    btnMarkAsUnseen.hidden = false;
  }
}

const CANDIDATE_STATUSES = {
  NOT_APPLIED:                  { apiValue: "Not applied",                  label: "Non candidaté" },
  WAITING_APPLICATION_RESPONSE: { apiValue: "Waiting Application Response", label: "En attente de réponse" },
  INTERVIEW:                    { apiValue: "Interview",                    label: "Entretien" },
  WAITING_INTERVIEW_RESPONSE:   { apiValue: "Waiting Interview Response",   label: "En attente (entretien)" },
  REJECTED:                     { apiValue: "Rejected",                     label: "Refusé" },
  ACCEPTED:                     { apiValue: "Accepted",                     label: "Embauché" },
};

const STATUS_TRANSITIONS = {
  NOT_APPLIED: [
    { to: 'WAITING_APPLICATION_RESPONSE', dateMode: 'now' },
  ],
  WAITING_APPLICATION_RESPONSE: [
    { to: 'WAITING_APPLICATION_RESPONSE', dateMode: 'now' },
    { to: 'INTERVIEW', dateMode: 'custom' },
    { to: 'REJECTED', dateMode: 'now' },
  ],
  INTERVIEW: [
    { to: 'WAITING_INTERVIEW_RESPONSE', dateMode: 'now' },
    { to: 'ACCEPTED', dateMode: 'now' },
    { to: 'REJECTED', dateMode: 'now' },
  ],
  WAITING_INTERVIEW_RESPONSE: [
    { to: 'WAITING_INTERVIEW_RESPONSE', dateMode: 'now' },
    { to: 'ACCEPTED', dateMode: 'now' },
    { to: 'REJECTED', dateMode: 'now' },
  ],
  ACCEPTED: [
      { to: 'REJECTED', dateMode: 'now' },
  ],
  REJECTED: [
    { to: 'NOT_APPLIED', dateMode: 'unchanged' },
  ],
};

function pad(n) { return String(n).padStart(2, '0'); }

// Formats a Date as "YYYY-MM-DD HH:MM:SS", matching the backend's strptime format.
function formatDateForApi(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} `
       + `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

// Formats a Date for an <input type="datetime-local"> value.
function formatDateForInput(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T`
       + `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function sendCandidateStatus(id, statusName, dateStr) {
  const apiValue = CANDIDATE_STATUSES[statusName].apiValue;
  let url = `/api/update_candidate_status/${id}?candidate_status=${encodeURIComponent(apiValue)}`;
  if (dateStr) url += `&candidate_date=${encodeURIComponent(dateStr)}`;
  const res = await fetch(url, { method: 'POST' });
  return res.ok;
}

function applyStatusToDom(offreEl, statusName, candidateDate) {
  const btn = offreEl.querySelector('.btn-statut');
  const oldStatus = btn.dataset.status;

  btn.classList.remove(`statut-${oldStatus.toLowerCase()}`);
  btn.classList.add(`statut-${statusName.toLowerCase()}`);
  btn.dataset.status = statusName;
  btn.querySelector('.statut-label').textContent = CANDIDATE_STATUSES[statusName].label;

  // Terminal statuses (Accepted/Rejected) no longer show a dropdown caret or menu.
  const caret = btn.querySelector('.statut-caret');
  const isTerminal = STATUS_TRANSITIONS[statusName].length === 0;
  if (isTerminal && caret) caret.remove();

  offreEl.dataset.candidateStatus = statusName;
  if (candidateDate) {
    offreEl.dataset.candidateDate = candidateDate.toISOString();

    const formatter = new Intl.DateTimeFormat("fr-FR", {
      timeZone: "Europe/Paris",
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    const parts = formatter.formatToParts(candidateDate);
    const values = Object.fromEntries(
      parts.map(({ type, value }) => [type, value])
    );
    const dateForDisplay = `le ${values.day}/${values.month} à ${values.hour}:${values.minute}`;

    const candidate_date = offreEl.querySelector('.candidate-date');
    candidate_date.hidden = false;
    if (statusName.toLowerCase() === 'interview') {
      candidate_date.innerText = "Date de l'entretien : " + dateForDisplay;
    }
    else {
      candidate_date.innerText = "Dernière action : " + dateForDisplay;
    }
  }
}

function closeAllStatusMenus() {
  document.querySelectorAll('.statut-menu').forEach(m => {
    m.hidden = true;
    m.innerHTML = '';
  });
}

function buildStatusMenuItems(menu, offreEl, currentStatus) {
  menu.innerHTML = '';
  const transitions = STATUS_TRANSITIONS[currentStatus] || [];

  transitions.forEach(t => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'statut-menu-item';
    if (currentStatus === t.to) {
      item.textContent = "Envoie d'une relance";
    }
    else {
      item.textContent = CANDIDATE_STATUSES[t.to].label;
    }
    item.dataset.to = t.to;
    item.dataset.dateMode = t.dateMode;
    menu.appendChild(item);
  });
}

function showDateForm(menu, offreEl, id, toStatus) {
  menu.innerHTML = '';
  menu.hidden = false;
  const form = document.createElement('div');
  form.className = 'statut-date-form';
  form.innerHTML = `
    <label>Date de l'entretien
      <input type="datetime-local" class="statut-date-input" value="${formatDateForInput(new Date())}">
    </label>
    <div class="statut-date-actions">
      <button type="button" class="btn-confirmer-date">Confirmer</button>
      <button type="button" class="btn-annuler-date">Annuler</button>
    </div>
  `;
  menu.appendChild(form);

  form.querySelector('.btn-annuler-date').addEventListener('click', () => {
    closeAllStatusMenus();
  });

  form.querySelector('.btn-confirmer-date').addEventListener('click', async () => {
    const input = form.querySelector('.statut-date-input');
    if (!input.value) return;
    const chosenDate = new Date(input.value);
    const dateStr = formatDateForApi(chosenDate);
    const ok = await sendCandidateStatus(id, toStatus, dateStr);
    if (ok) {
      applyStatusToDom(offreEl, toStatus, chosenDate);
    }
    closeAllStatusMenus();
  });
}

liste.addEventListener('click', async (e) => {
  const offreEl = e.target.closest('.offre');
  if (!offreEl) return;
  const id = offreEl.dataset.id;

  const lienTitre = e.target.closest('.offre-titre');
  if (lienTitre) {
    markAsSeen(offreEl);
    return;
  }

  const btnLirePlus = e.target.closest('.btn-lire-plus');
  if (btnLirePlus) {
    openDescModal(btnLirePlus.dataset.title, btnLirePlus.dataset.full);
    return;
  }

  const btnMarkAsUnseen = e.target.closest('.btn-mark-as-unseen');
  if (btnMarkAsUnseen) {
    e.preventDefault();
    if (offreEl.dataset.vu === 'True') {
      offreEl.dataset.vu = 'False';
      offreEl.classList.remove('etat-vu');
      btnMarkAsUnseen.hidden = true;
      const res = await fetch(`/api/mark_as_unseen/${id}`, {method: 'POST'});
      if (!res.ok && offreEl.dataset.vu === 'False') {
        offreEl.dataset.vu = 'True';
        offreEl.classList.add('etat-vu');
        btnMarkAsUnseen.hidden = false;
      }
    }
  }

  // Toggle the status dropdown open/closed.
  const btnStatut = e.target.closest('.btn-statut');
  if (btnStatut) {
    e.preventDefault();
    const menu = offreEl.querySelector('.statut-menu');
    const alreadyOpen = !menu.hidden;
    closeAllStatusMenus();
    if (!alreadyOpen) {
      buildStatusMenuItems(menu, offreEl, btnStatut.dataset.status);
      if (menu.children.length > 0) menu.hidden = false;
    }
    return;
  }

  // Click on a menu item: either fire immediately, or show the date picker for "Entretien".
  const menuItem = e.target.closest('.statut-menu-item');
  if (menuItem) {
    e.preventDefault();
    const toStatus = menuItem.dataset.to;
    const dateMode = menuItem.dataset.dateMode;
    const menu = offreEl.querySelector('.statut-menu');

    if (dateMode === 'custom') {
      showDateForm(menu, offreEl, id, toStatus);
      return;
    }

    const dateStr = dateMode === 'now' ? formatDateForApi(new Date()) : null;
    const ok = await sendCandidateStatus(id, toStatus, dateStr);
    if (ok) {
      applyStatusToDom(offreEl, toStatus, dateStr ? new Date() : null);
      markAsSeen(offreEl);
      const res = await fetch(`/api/mark_as_seen/${id}`, {method: 'POST'});
      if (!res.ok && offreEl.dataset.vu === 'True') {
        offreEl.dataset.vu = 'False';
        offreEl.classList.remove('etat-vu');
        btnMarkAsUnseen.hidden = true;
      }
    }
    closeAllStatusMenus();
  }
});

// Set the initial French label on every status button on page load.
document.querySelectorAll('.btn-statut').forEach(btn => {
  const label = btn.querySelector('.statut-label');
  label.textContent = CANDIDATE_STATUSES[btn.dataset.status].label;
});

// Filtres
filter_buttons.forEach(btn => {
  btn.addEventListener('click', () => {
    filter_buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filtre = btn.dataset.filtre;
    jobs.forEach(job => {
      const vu = job.dataset.vu === 'True';
      const status = job.dataset.candidateStatus;
      const enCours = status !== 'NOT_APPLIED' && status !== 'REJECTED';
      let visible = true;
      if (filtre === 'non-vues') visible = !vu;
      else if (filtre === 'postulees') visible = enCours;
      else if (filtre === 'vues') visible = vu;
      job.style.display = visible ? '' : 'none';
    });
    job_count.innerHTML = get_job_count();

    const articles = Array.from(jobs);
    articles.sort((a, b) => {
      const da = a.dataset.candidateDate;
      const db = b.dataset.candidateDate;
      if (!da && !db) return 0;
      if (!da) return 1;   // no date -> pushed to the end
      if (!db) return -1;
      return new Date(da) - new Date(db); // oldest first
    });
    articles.forEach(el => liste.appendChild(el));
  });
});

// ---------- Modal description ----------

const descModal = document.getElementById('desc-modal');
const descModalTitle = document.getElementById('desc-modal-title');
const descModalBody = document.getElementById('desc-modal-body');

function openDescModal(title, text) {
  descModalTitle.textContent = title;
  descModalBody.textContent = text;
  descModal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeDescModal() {
  descModal.hidden = true;
  document.body.style.overflow = '';
}

descModal.querySelector('.modal-close').addEventListener('click', closeDescModal);
descModal.addEventListener('click', (e) => {
  if (e.target === descModal) closeDescModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !descModal.hidden) closeDescModal();
});
