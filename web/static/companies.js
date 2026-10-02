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
        }
        else {
            company.style.display = 'none';
        }
    });
    companyCount.innerHTML = count;
}
