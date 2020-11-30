//DOM
const $ = document.querySelector.bind(document);

//APP
let App = {};
App.init = (function () {
	//Init
	async function handleFileSelect(evt) {
		const files = evt.target.files; // FileList object
		//files template
		let template = `${Object.keys(files)
			.map(file => `<div class="file file--${file}">
     <div class="name"><span>${files[file].name}</span></div>
     <div class="progress active"></div>
     <div class="done">
	<a href="" target="_blank">
      <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" x="0px" y="0px" viewBox="0 0 1000 1000">
		<g><path id="path" d="M500,10C229.4,10,10,229.4,10,500c0,270.6,219.4,490,490,490c270.6,0,490-219.4,490-490C990,229.4,770.6,10,500,10z M500,967.7C241.7,967.7,32.3,758.3,32.3,500C32.3,241.7,241.7,32.3,500,32.3c258.3,0,467.7,209.4,467.7,467.7C967.7,758.3,758.3,967.7,500,967.7z M748.4,325L448,623.1L301.6,477.9c-4.4-4.3-11.4-4.3-15.8,0c-4.4,4.3-4.4,11.3,0,15.6l151.2,150c0.5,1.3,1.4,2.6,2.5,3.7c4.4,4.3,11.4,4.3,15.8,0l308.9-306.5c4.4-4.3,4.4-11.3,0-15.6C759.8,320.7,752.7,320.7,748.4,325z"</g>
		</svg>
						</a>
     </div>
    </div>`)
			.join("")}`;

		$("#drop").classList.add("hidden");
		$("footer").classList.add("hasFiles");
		$(".importar").classList.add("active");

		$(".list-files").innerHTML = template;

		for (const file of Object.keys(files)) {
			let formData = new FormData();
			let xls = files[0]

			formData.append("xls", xls);

			try {
				let r = await fetch('/upload', { method: "POST", body: formData });
				console.log('HTTP response code:', r.status);
				if (r.ok === true) {
					$(`.file--${file}`).querySelector(".progress").classList.remove("active");
					$(`.file--${file}`).querySelector(".done").classList.add("anim");
					data = await r.json();
					$("#result").src = data["image"];
					missing_ids = data["missing_ids"];
					for (let i = 0; i < missing_ids.length; i++) {
						missing = missing_ids[i];
						tr = document.createElement("tr");
						product_id = document.createElement("td");
						product_id.appendChild(document.createTextNode(missing.id));
						product_name = document.createElement("td");
						product_name.appendChild(document.createTextNode(missing.name));
						tr.appendChild(product_id);
						tr.appendChild(product_name);
						$("#missing").appendChild(tr);
					}
					$("#missing").style.display="";
				} else {
					try {
						data = await r.json();
						$("#result").src = data["image"];
					} catch (e) {
						$("#result").src = "https://i.giphy.com/media/RJaUOmpBQAoE4RuWnj/source.gif";
					}
				}
				$("#result").style.display="";
			} catch (e) {
				console.log('Huston we have problem...:', e);
			}
		};
	}

	// trigger input
	$("#triggerFile").addEventListener("click", evt => {
		evt.preventDefault();
		$("input[type=file]").click();
	});

	// drop events
	$("#drop").ondragleave = evt => {
		$("#drop").classList.remove("active");
		evt.preventDefault();
	};
	$("#drop").ondragover = $("#drop").ondragenter = evt => {
		$("#drop").classList.add("active");
		evt.preventDefault();
	};
	$("#drop").ondrop = evt => {
		$("input[type=file]").files = evt.dataTransfer.files;
		$("footer").classList.add("hasFiles");
		$("#drop").classList.remove("active");
		evt.preventDefault();
	};

	//upload more
	$(".importar").addEventListener("click", () => {
		$(".list-files").innerHTML = "";
		$("footer").classList.remove("hasFiles");
		$(".importar").classList.remove("active");
		$("#result").style.display="none";
		$("#missing").style.display="none";
		$("#missing").innerHTML = "";
		// clear input to allow using the same file
		$("input").value = '';
		setTimeout(() => {
			$("#drop").classList.remove("hidden");
		}, 500);
	});

	// input change
	$("input[type=file]").addEventListener("change", handleFileSelect);
})();
