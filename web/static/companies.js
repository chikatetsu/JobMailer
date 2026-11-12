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
        openEditModal(
            company.dataset.id,
            company.dataset.name,
            company.dataset.address,
            company.dataset.hiring,
            company.dataset.website,
            company.dataset.siren,
            company.dataset.tranch_employees,
            company.dataset.main_activity,
            company.dataset.company_type,
            company.dataset.is_siege
        );
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
const editModalAddress = document.getElementById('edit-modal-address');
const editModalHiring = document.getElementById('edit-modal-hiring');
const editModalWebsite = document.getElementById('edit-modal-website');
const editModalSiren = document.getElementById('edit-modal-siren');
const editModalTranchEmployees = document.getElementById('edit-modal-tranch-employees');
const editModalMainActivity = document.getElementById('edit-modal-main-activity');
const editModalCompanyType = document.getElementById('edit-modal-company-type');
const editModalIsSiege = document.getElementById('edit-modal-is-siege');
const editModalCancel = document.getElementById('edit-modal-cancel');
const editModalSave = document.getElementById('edit-modal-save');

function openEditModal(companyId, companyName, companyAddress, companyHiring, companyWebsite, companySiren, companyTranchEmployees, companyMainActivity, companyType, companyIsSiege) {
    editModalId.innerText = companyId;
    editModalName.value = companyName;
    editModalAddress.value = companyAddress;
    editModalHiring.value = companyHiring;
    editModalWebsite.value = companyWebsite;
    editModalSiren.value = companySiren;
    editModalTranchEmployees.value = companyTranchEmployees;
    editModalMainActivity.value = companyMainActivity;
    editModalCompanyType.value = companyType;
    editModalIsSiege.value = companyIsSiege;
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
        address: editModalAddress.value,
        hiring: editModalHiring.value,
        website: editModalWebsite.value,
        siren: editModalSiren.value,
        tranch_employees: editModalTranchEmployees.value,
        main_activity: editModalMainActivity.value,
        company_type: editModalCompanyType.value,
        is_siege: editModalIsSiege.value
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
