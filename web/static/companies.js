const companies = document.getElementById('liste-entreprises');

companies.addEventListener('click', async (e) => {
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
