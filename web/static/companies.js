const companyList = document.getElementById('liste-entreprises');
const companies = document.querySelectorAll('#liste-entreprises .company-card');
const searchbar = document.getElementById('searchbar');
const companyCount = document.getElementById('companyCount');

let getCompanyCount = () => {
    let cpt = 0;
    companies.forEach(company => {
        if (company.style.display !== 'none') cpt += 1;
    });
    return cpt;
};
companyCount.innerHTML = getCompanyCount();

companyList.addEventListener('click', async (e) => {
    const company = e.target.closest('.company-card');
    if (!company)
        return;
    const id = company.dataset.id;

    // Spontaneous application
    const btnCandidate = e.target.closest('.btn-candidate');
    if (btnCandidate) {
        e.preventDefault();
        const container = company.querySelector('.candidate-container');
        container.innerHTML = '<div class="candidate-tag">Candidaté!</div>';
        const res = await fetch(`/api/create_spontaneous_application/${id}`, {method: 'POST'});
        if (!res.ok) {
            container.innerHTML = '<button class="btn-candidate">Candidature spontanée</button>';
        }
        return;
    }

    // Edit modal
    const btnEdit = e.target.closest('.btn-modifier');
    if (btnEdit) {
        e.preventDefault();
        openEditModal(company.dataset.id, company.dataset.name, company.dataset.hiring, company.dataset.website);
        return;
    }
});

// Search bar for companies
let searchTimeout;
searchbar.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchCompany();
    }, 200);
});

function searchCompany() {
    const input = searchbar.value.toLowerCase();
    let count = 0;
    companies.forEach((company) => {
        if (company.innerText.toLowerCase().includes(input) || input === '') {
            company.style.display = '';
            count += 1;
        } else {
            company.style.display = 'none';
        }
    });
    companyCount.innerHTML = count;
}

// Modal edit
const editModal = document.getElementById('edit-modal');
const editModalId = document.getElementById('edit-modal-id');
const editModalName = document.getElementById('edit-modal-name');
const editModalHiring = document.getElementById('edit-modal-hiring');
const editModalWebsite = document.getElementById('edit-modal-website');
const editModalCancel = document.getElementById('edit-modal-cancel');
const editModalSave = document.getElementById('edit-modal-save');

function openEditModal(companyId, companyName, companyHiring, companyWebsite) {
    editModalId.innerText = companyId;
    editModalName.value = companyName;
    editModalHiring.value = companyHiring;
    editModalWebsite.value = companyWebsite;
    editModal.hidden = false;
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    editModal.hidden = true;
    document.body.style.overflow = '';
}
async function editCompany() {
    const url = `/api/edit_company/${editModalId.innerText}`;
    const data = {
        name: editModalName.value,
        hiring: editModalHiring.value,
        website: editModalWebsite.value,
    };
    const response = await fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    return await response.json();
}

editModalCancel.addEventListener('click', (e) => {
    e.preventDefault();
    closeEditModal();
});
editModalSave.addEventListener('click', async (e) => {
    e.preventDefault();
    editModalSave.innerText = 'Sauvegarde...';
    await editCompany();
    closeEditModal();
    window.location.reload();
});
editModal.addEventListener('click', (e) => {
    if (e.target === editModal) closeEditModal();
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !editModal.hidden) closeEditModal();
});
