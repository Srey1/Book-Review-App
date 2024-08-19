const picture = document.querySelector('.icon');
const file = document.querySelector('#filee');

file.addEventListener('change', function() {
    const chosen = this.files[0];
    if (chosen) {
        const reader = new FileReader();
        reader.addEventListener('load', function() {
            picture.setAttribute('src', reader.result);
        })

        reader.readAsDataURL(chosen);
    } 
});