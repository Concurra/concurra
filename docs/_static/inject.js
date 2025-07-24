// inject.js

document.addEventListener("DOMContentLoaded", function () {
  const logo = document.querySelector(".wy-side-nav-search .logo");

  if (logo) {
    // Main container below the logo
    const container = document.createElement("div");
    container.style.textAlign = "center";
    container.style.marginTop = "10px";

    // Horizontal separator
    const hr = document.createElement("hr");
    hr.style.border = "0";
    hr.style.height = "1px";
    hr.style.backgroundColor = "#ffffff";
    hr.style.margin = "12px 20px";

    // Author heading
    const authorHeading = document.createElement("div");
    authorHeading.textContent = "Author";
    authorHeading.style.fontSize = "0.8rem";
    authorHeading.style.fontWeight = "bold";
    authorHeading.style.color = "#ffffff";
    authorHeading.style.margin = "10px 0 6px";

    // Author row container (image + name)
    const authorContainer = document.createElement("div");
    authorContainer.style.display = "flex";
    authorContainer.style.flexDirection = "column";
    authorContainer.style.alignItems = "center";
    authorContainer.style.justifyContent = "center";

    // LinkedIn URL
    const linkedInURL = "https://www.linkedin.com/in/sahilrp7/";

    // Profile photo (linked)
    const profileLink = document.createElement("a");
    profileLink.href = linkedInURL;
    profileLink.target = "_blank";
    profileLink.rel = "noopener noreferrer";

    const img = document.createElement("img");
    img.src = "https://media.licdn.com/dms/image/v2/C5603AQFC5bfS-Hr7Ew/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1657593394478?e=1756339200&v=beta&t=mkCt3xn6bePUAeehxS2cbBg3L4emrTGY-GOiYDX2BNg";
    img.alt = "Sahil Pardeshi";
    img.style.width = "70px";
    img.style.height = "70px";
    img.style.borderRadius = "50%";
    img.style.objectFit = "cover";
    img.style.marginBottom = "3px";

    profileLink.appendChild(img);

    // Author name (linked)
    const nameLink = document.createElement("a");
    nameLink.href = linkedInURL;
    nameLink.target = "_blank";
    nameLink.rel = "noopener noreferrer";
    nameLink.textContent = "Sahil Pardeshi";
    nameLink.style.color = "#ffffff";
    nameLink.style.fontSize = "0.8rem";
    nameLink.style.textDecoration = "none";
    nameLink.style.marginTop = "2px";

    // Build author block
    authorContainer.appendChild(profileLink);
    authorContainer.appendChild(nameLink);

    // Append everything in order
    container.appendChild(hr);
    container.appendChild(authorHeading);
    container.appendChild(authorContainer);

    // Insert container after logo
    logo.insertAdjacentElement("afterend", container);
  }

  // Hide version selector completely
  const versionBox = document.querySelector(".rst-versions");
  if (versionBox) {
    versionBox.style.display = "none";
    versionBox.style.visibility = "hidden";
    versionBox.style.height = "0";
    versionBox.style.padding = "0";
    versionBox.style.margin = "0";
  }
});

// Reset scroll position on page load to prevent auto-scroll
window.addEventListener("load", function () {
  if (window.location.hash) {
    history.replaceState(null, null, " ");
  }
  window.scrollTo(0, 0);
});
