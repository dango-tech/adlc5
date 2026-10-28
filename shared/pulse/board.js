const data = JSON.parse(document.getElementById("snapshot").textContent);
const selector = document.getElementById("feature");
const panel = document.getElementById("features");
const stages = ["specify", "plan", "tasks", "implement"];
const make = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const money = value => typeof value === "number" ? `$${value.toFixed(2)}` : "Unavailable";
const label = value => value ? String(value).replaceAll("_", " ") : "Not recorded";
const statusClass = value => ["pass", "completed"].includes(value) ? "p-good" : ["fail", "unstable"].includes(value) ? "p-bad" : "p-warn";
const hostNames = {claude: "Claude Code", codex: "Codex", cursor: "Cursor", hermes: "Hermes Agent"};
// Agent marks: @lobehub/icons-static-svg 1.100.0 (MIT); Hermes Agent uses its maker's Nous Research mark.
const hostMarks = {"claude":["M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z"],"codex":["M8.086.457a6.105 6.105 0 013.046-.415c1.333.153 2.521.72 3.564 1.7a.117.117 0 00.107.029c1.408-.346 2.762-.224 4.061.366l.063.03.154.076c1.357.703 2.33 1.77 2.918 3.198.278.679.418 1.388.421 2.126a5.655 5.655 0 01-.18 1.631.167.167 0 00.04.155 5.982 5.982 0 011.578 2.891c.385 1.901-.01 3.615-1.183 5.14l-.182.22a6.063 6.063 0 01-2.934 1.851.162.162 0 00-.108.102c-.255.736-.511 1.364-.987 1.992-1.199 1.582-2.962 2.462-4.948 2.451-1.583-.008-2.986-.587-4.21-1.736a.145.145 0 00-.14-.032c-.518.167-1.04.191-1.604.185a5.924 5.924 0 01-2.595-.622 6.058 6.058 0 01-2.146-1.781c-.203-.269-.404-.522-.551-.821a7.74 7.74 0 01-.495-1.283 6.11 6.11 0 01-.017-3.064.166.166 0 00.008-.074.115.115 0 00-.037-.064 5.958 5.958 0 01-1.38-2.202 5.196 5.196 0 01-.333-1.589 6.915 6.915 0 01.188-2.132c.45-1.484 1.309-2.648 2.577-3.493.282-.188.55-.334.802-.438.286-.12.573-.22.861-.304a.129.129 0 00.087-.087A6.016 6.016 0 015.635 2.31C6.315 1.464 7.132.846 8.086.457zm-.804 7.85a.848.848 0 00-1.473.842l1.694 2.965-1.688 2.848a.849.849 0 001.46.864l1.94-3.272a.849.849 0 00.007-.854l-1.94-3.393zm5.446 6.24a.849.849 0 000 1.695h4.848a.849.849 0 000-1.696h-4.848z"],"cursor":["M22.106 5.68L12.5.135a.998.998 0 00-.998 0L1.893 5.68a.84.84 0 00-.419.726v11.186c0 .3.16.577.42.727l9.607 5.547a.999.999 0 00.998 0l9.608-5.547a.84.84 0 00.42-.727V6.407a.84.84 0 00-.42-.726zm-.603 1.176L12.228 22.92c-.063.108-.228.064-.228-.061V12.34a.59.59 0 00-.295-.51l-9.11-5.26c-.107-.062-.063-.228.062-.228h18.55c.264 0 .428.286.296.514z"],"hermes":["M5.938 12.835c.127-.039.285.02.373.143.028.038.036.092.046.14.003.014-.02.033-.04.05-.124-.098-.24-.194-.354-.291-.011-.01-.016-.027-.025-.042zM8.396 9.412c.195-.032.39-.06.588-.05a.54.54 0 01.148.026c.202.071.402.147.601.224.028.01.05.036.075.055l-.013.027a9.203 9.203 0 01-.26-.089c-.115-.038-.213-.077-.315-.098-.25-.05-.25-.046-.292-.014l.574.144c.275.139.55.276.823.417.042.022.09.057.107.098.026.06.063.076.117.072.066-.006.132-.017.213-.027l-.04.086c.051.08.142.02.216.064-.074.13-.247.09-.334.199l.061.074-.12.087c0 .106-.038.168-.306.243l.026.085-.196.042.07.124h-.25l-.007.137c-.081-.01-.161-.018-.244-.027l-.053.123c-.027-.008-.052-.011-.073-.023-.067-.038-.128-.056-.195.006-.019.017-.063.014-.093.008-.026-.006-.05-.029-.07-.042-.11.095-.11.095-.208.003-.057.046-.12.074-.186.011-.063.027-.123-.02-.178-.014-.07.007-.097-.035-.133-.07l-.13.033c-.013-.236-.194-.19-.34-.203.005-.072.05-.092.095-.094a.474.474 0 01.159.022c.164.05.32.12.496.138.203.021.405.029.601-.015.265-.059.52-.149.707-.365.049-.056.083-.127.117-.195.019-.038.02-.084-.02-.116a1.397 1.397 0 00-.382-.217c.024.12-.031.182-.115.221 0 .014-.004.025 0 .03.08.115.084.16-.007.267a1.39 1.39 0 01-.218.211.477.477 0 01-.641-.05 1.36 1.36 0 01-.133-.152c-.078-.107-.076-.108-.033-.236-.165-.08-.128-.226-.104-.364.008-.05.028-.096.049-.163-.04.014-.067.017-.087.032a.897.897 0 00-.316.357c-.007.016-.01.034-.02.047-.012.015-.034.038-.045.035-.02-.006-.037-.027-.05-.045-.008-.012-.007-.032-.012-.057h-.126l.053-.172a14.82 14.82 0 00-.039-.049l.11-.284c-.06.026-.091.044-.124.051-.03.007-.064 0-.095 0 0-.031-.01-.07.004-.092.149-.22.305-.428.593-.476z","M8.06 10.788c-.003-.038-.004-.075.037-.062.016.006.034.048.028.067-.01.04-.038.032-.064-.005z","M11.981.009c.226-.012.453-.011.679 0 .247.01.495.024.74.062.401.064.798.157 1.19.273.463.138.92.299 1.356.511a7.31 7.31 0 012.948 2.642c.292.469.536.963.739 1.479.219.556.446 1.11.623 1.683.204.654.329 1.326.458 1.997.097.504.182 1.01.29 1.511.156.722.329 1.44.494 2.16.186.812.4 1.615.63 2.415.102.355.193.713.282 1.072.11.436.202.876.254 1.323.031.278.066.557.073.837a7.56 7.56 0 01-.017.88c-.037.413-.1.818-.226 1.212a5.017 5.017 0 01-.915 1.649l-.13.156.018.023c.043-.023.088-.041.127-.068.2-.138.373-.307.531-.49.4-.46.721-.973.975-1.529a3.59 3.59 0 00.325-1.72c-.024-.424-.097-.834-.3-1.213-.013-.027-.015-.06-.03-.121.05.035.082.048.101.072.107.13.22.258.315.398.33.494.46 1.052.486 1.64a3.75 3.75 0 01-.47 1.97c-.36.655-.887 1.14-1.526 1.506-.193.111-.394.21-.595.308-.157.078-.248.211-.318.365a.522.522 0 00-.033.406.359.359 0 01.013.139c-.005.077-.077.155-.14.162-.054.006-.125-.043-.15-.116a1.206 1.206 0 01-.06-.233c-.04-.314-.155-.6-.308-.87a3.906 3.906 0 00-.73-.91 2.129 2.129 0 00-.897-.524 4.093 4.093 0 00-.692-.131c-.075-.008-.15-.04-.22.01.18.06.363.11.538.18.434.173.82.43 1.18.728.308.255.58.543.794.884.098.155.186.315.227.496.027.123.042.25.067.375.013.062-.002.109-.053.144-.047.033-.122.034-.163-.01a.455.455 0 01-.08-.14c-.03-.073-.038-.159-.078-.225a7.314 7.314 0 00-1.423-1.664c-.16-.137-.329-.26-.537-.323-.376-.114-.753-.203-1.15-.154-.213.025-.427.032-.64.053a1.6 1.6 0 00-.736.278 5.14 5.14 0 00-.834.72c-.329.342-.642.699-.955 1.055-.136.155-.264.319-.314.531a5.227 5.227 0 00-.012.051.096.096 0 01-.09.076h-.31c-.046 0-.082-.048-.072-.094.023-.108.045-.216.07-.324.075-.325.19-.635.368-.917.024-.039.04-.088.104-.08l.01.049.027.077c.28-.435.571-.834.996-1.135.283-.204.584-.378.89-.55a.196.196 0 00-.098-.002c-.162.043-.325.084-.485.134-.402.124-.764.33-1.11.566-.147.1-.298.193-.414.333a7.314 7.314 0 00-1.07 1.767.845.845 0 00-.04.12.075.075 0 01-.072.056h-.494c-.04 0-.062-.051-.036-.082.123-.14.246-.282.377-.415.275-.281.58-.532.777-.884.027-.048.063-.09.095-.135.238-.333.54-.607.818-.902.082-.086.175-.16.26-.24.029-.027.053-.057.079-.085l-.018-.025-.135.041c-.034.017-.07.031-.102.05-.248.144-.494.292-.743.433-.408.23-.825.439-1.209.711-.281.2-.591.358-.889.533-.02.012-.044.015-.08.028-.015-.135.143-.201.108-.336-.033.014-.064.02-.085.038-.111.096-.227.19-.328.296-.148.157-.284.325-.425.488-.125.143-.25.286-.373.431A.153.153 0 019.89 24H8.762a.316.316 0 00.016-.042c.028-.09.085-.172.083-.28-.091-.018-.162.001-.212.077a4.45 4.45 0 00-.136.215c-.01.016-.024.03-.042.03h-.093c-.019 0-.029-.022-.017-.037.071-.088.14-.178.209-.268.001-.002-.006-.012-.012-.024-.014.004-.03.006-.045.013-.176.09-.352.181-.527.274a.363.363 0 01-.168.042H5.202c-.026 0-.039-.036-.019-.053.21-.178.402-.374.558-.605.335-.496.538-1.047.667-1.629.004-.02-.003-.043-.006-.091-.037.048-.059.072-.076.1a1.943 1.943 0 01-.334.415c-.28.258-.59.448-.983.464-.297.012-.588 0-.865-.127-.46-.21-.722-.57-.794-1.072-.025-.17-.017-.171-.182-.219A3.513 3.513 0 011.97 20.6a2.286 2.286 0 01-.808-1.13 3.569 3.569 0 01-.16-1.245c.002-.034.016-.067.024-.1.032.023.046.043.05.066.033.153.059.308.096.46.086.355.257.664.516.92.258.256.571.419.91.532.358.118.717.138 1.07-.016a1.89 1.89 0 00.621-.452c.328-.348.533-.76.648-1.223.009-.034.005-.071.007-.11-.015.006-.026.006-.03.011-.031.05-.064.1-.093.152-.284.502-.679.887-1.196 1.135-.351.17-.718.255-1.11.159a1.607 1.607 0 01-.971-.64 2.006 2.006 0 01-.368-.924 2.903 2.903 0 01.02-.886c.05-.439.466-1.17.742-1.271-.02.063-.035.112-.053.16-.043.116-.097.227-.13.345a1.901 1.901 0 00-.05.82c.033.212.09.416.204.6.147.236.346.407.62.465.11.023.225.014.338.018a.576.576 0 00.386-.131c.164-.128.282-.292.366-.481.168-.375.24-.777.309-1.179.05-.296.093-.594.133-.893.039-.281.071-.563.104-.845.026-.232.048-.464.074-.696.024-.228.052-.455.076-.683.024-.227.047-.455.069-.683.013-.14.022-.28.034-.42l.037-.417c.022-.25.041-.5.065-.748.008-.082-.02-.132-.09-.177a2.46 2.46 0 01-.492-.418c-.1-.109-.188-.228-.282-.342-.035-.042-.056-.097-.116-.118a2.084 2.084 0 00.275.597c.06.092.131.176.196.265.063.086.182.115.234.226-.028.003-.046.01-.06.006a4.74 4.74 0 01-.22-.057 2.71 2.71 0 01-1.287-.819c-.435-.487-.656-1.076-.71-1.723a5.206 5.206 0 01.014-1.06c.072-.602.22-1.186.45-1.745.155-.376.338-.741.526-1.102.205-.393.466-.75.765-1.076.512-.559 1.104-1.024 1.726-1.448.717-.49 1.478-.898 2.277-1.233C8.244.828 8.767.632 9.31.494c.655-.166 1.31-.33 1.982-.415.229-.03.458-.058.688-.07zm-1.847 22.82c-.07.06-.147.111-.207.18-.238.27-.464.549-.668.869l-.044.108a.177.177 0 00.093-.057c.174-.19.351-.378.519-.574.104-.122.195-.255.288-.386.024-.034.03-.08.046-.12l-.027-.02zm1.65-3.695a5.51 5.51 0 00-.653.593l-.37.386a.963.963 0 01-.377.25 1.372 1.372 0 01-.467.09c-.044 0-.087.006-.151.012.028.058.043.097.064.131.15.242.301.482.45.724.136.22.276.438.399.666.068.125.105.267.156.404.077.027.14-.018.202-.048.29-.135.579-.274.867-.412.213-.101.437-.186.636-.31.347-.215.68-.455 1.018-.685.015-.01.026-.028.042-.046-.023-.019-.038-.037-.056-.044-.287-.111-.527-.3-.77-.482a5.319 5.319 0 01-.506-.42 1.757 1.757 0 01-.41-.653c-.019-.049-.045-.095-.075-.156zm-5.847.264c-.06.096-.097.194-.132.293a3.38 3.38 0 01-.555 1.01c-.2.25-.455.412-.762.493-.23.06-.464.076-.7.07-.048-.002-.097.002-.158.005.016.04.021.066.035.085.1.145.23.246.4.295.157.046.316.034.498.023.181-.037.343-.115.485-.234.238-.199.402-.454.536-.732.175-.363.264-.751.342-1.144.01-.053.008-.11.011-.164zm14.945-4.586c.008.029.016.057.027.107.024.155.051.31.072.464.03.219.067.437.078.657.017.344.027.689-.014 1.033-.037.315-.063.633-.116.946a6.153 6.153 0 01-.46 1.518c-.008.018-.01.039-.02.082.047-.03.077-.042.098-.064.085-.083.17-.167.248-.255.271-.305.458-.66.596-1.043.18-.498.228-1.011.145-1.531-.103-.65-.33-1.263-.597-1.881a9.055 9.055 0 00-.024-.055l-.033.022zM5.797 8.29a.26.26 0 00.018.153c.124.251.25.501.379.75.025.049.066.09.03.163-.284.06-.578.119-.88.255.059.038.097.06.132.087.042.032.112.058.09.12-.01.033-.075.048-.117.072.017.01.043.021.067.036.166.102.33.207.447.368.138.192.229.404.188.644-.079.469-.306.85-.69 1.132-.054.04-.106.083-.161.122a.243.243 0 00-.103.245.77.77 0 00.055.195c.083.196.22.35.375.492.083.076.159.164.222.257a.37.37 0 01.025.377c-.023.05-.05.099-.076.148-.03.06-.028.111.022.162.041.042.08.089.112.138.038.058.078.079.147.05a.486.486 0 01.333-.006c.16.046.302.126.444.21.13.077.264.149.4.219.067.035.14.05.219.026.071-.022.124.01.145.076.02.064-.003.108-.074.139-.07.03-.137.063-.209.088-.1.035-.201.073-.314.077-.013-.107.11-.088.127-.159-.206-.126-.643-.145-.801-.034.063.112.035.21-.096.313-.13-.1-.025-.202.002-.3a.209.209 0 00-.249.17c-.015.101.067.216.178.224.108.007.218-.005.326-.012.06-.005.12-.027.199 0-.103.123-.248.127-.357.19.002.05.07.086.019.131-.053.048-.095-.001-.132-.03-.08-.063-.16-.126-.231-.197a.474.474 0 01-.157-.311.52.52 0 00-.043-.172c-.032-.074-.032-.137.033-.19-.018-.03-.028-.053-.045-.072a1.222 1.222 0 01-.196-.369c-.053-.137-.046-.264.048-.381.024-.03.05-.06.064-.095a.664.664 0 00.047-.168c.017-.165-.064-.287-.182-.387-.186-.156-.36-.322-.46-.551-.005-.011-.024-.017-.037-.026-.011.017-.024.027-.025.038-.019.185-.045.37-.052.557-.014.377.058.743.162 1.104.118.41.289.798.488 1.173.267.502.537 1.002.812 1.5.055.098.13.189.208.27.198.202.452.272.724.273.202 0 .404-.006.605-.026.295-.03.59-.073.884-.113.183-.025.365-.057.548-.08.21-.026.38.073.522.21.16.156.305.327.447.5.22.265.397.56.554.867.05.098.07.1.147.03.13-.121.26-.242.394-.36.067-.059.088-.12.067-.213a3.535 3.535 0 01-.085-.796c.002-.157.006-.314.018-.471.015-.224.03-.45.06-.672a59.114 59.114 0 01.362-2.298c.087-.493.182-.984.268-1.477.06-.347.118-.694.162-1.043.034-.273.055-.55.063-.825.011-.332.003-.665.002-.998 0-.077.004-.155-.01-.23-.028-.142-.01-.155-.162-.19a5.826 5.826 0 00-.607-.107c-.146-.018-.207-.053-.221-.19-.006-.049-.025-.098-.041-.146-.009-.025-.024-.048-.046-.09l-.025.264c-.009.096-.029.116-.127.115-.055 0-.11-.008-.164-.008-.476 0-.952-.008-1.426.032-.095.008-.173-.015-.226-.103-.04-.066-.088-.126-.134-.186-.063-.084-.086-.093-.182-.06-.195.068-.388.138-.582.21a2.71 2.71 0 00-.675.394.986.986 0 01-.323.168c-.033.01-.07.008-.127.013.02-.066.024-.114.047-.15.064-.105.135-.205.205-.306.023-.033.049-.063.073-.095l-.015-.023-.201.037c-.146.04-.296.07-.437.122-.148.053-.266.023-.386-.072a3.623 3.623 0 01-.733-.786l-.093-.132zm8.592 8.963l-.147.09c-.22.134-.44.266-.659.402-.093.058-.184.12-.27.188-.085.07-.124.161-.072.272.047.1.093.2.147.294.047.08.124.138.213.147.11.01.228.012.336-.012.217-.05.372-.205.528-.357a.291.291 0 00.087-.308c-.046-.18-.079-.365-.118-.547-.011-.052-.027-.103-.045-.169zm-.257-2.409c-.12.291-.205.597-.325.91-.151.433-.294.87-.435 1.323.036-.01.054-.01.067-.018.261-.16.522-.324.785-.484.054-.033.071-.078.065-.138-.012-.13-.024-.262-.034-.393l-.068-.886c-.008-.103-.02-.206-.029-.31-.009 0-.017-.002-.026-.004zm3.081-8.13l.099.285c.08.231.159.463.24.714l.58 1.952c.187.63.372 1.262.558 1.893.114.382.235.762.343 1.146.072.257.126.519.186.799.044.206.087.413.127.64.034.106.023.226.077.325l.025-.006-.068-.362c-.038-.206-.077-.412-.113-.638-.015-.07-.029-.141-.046-.211-.095-.396-.177-.796-.29-1.187-.196-.685-.413-1.364-.618-2.046-.165-.549-.322-1.1-.488-1.648-.069-.227-.15-.45-.226-.695l-.117-.336c-.037-.107-.075-.216-.115-.322-.04-.106-.084-.21-.127-.314a7.558 7.558 0 01-.027.01zM6.225 14.304c-.063-.001-.115.014-.134.083a.35.35 0 00.41.012 4.533 4.533 0 00-.276-.095zM5.23 11.98c-.026-.027-.057-.048-.075.002-.012.032-.007.07-.01.113.082-.037.082-.037.085-.115zm.062-1.189a.135.135 0 00-.088.056.197.197 0 00-.025.11c.005.152.01.306.026.457a.751.751 0 00.066.218c.061.136.157.167.288.101.055-.027.06-.054.025-.11a4.52 4.52 0 01-.129-.211c-.015-.068-.066-.131-.033-.207.04-.09-.076-.116-.074-.19V10.874c-.003-.038-.006-.087-.056-.083zm-.017-.968a.867.867 0 00-.467.127c-.076.045-.084.07-.05.158.034.087.07.173.115.254.064.117.09.125.21.077a.657.657 0 01.336-.053c.202.022.357.136.504.264l.092.077c.007-.006.014-.013.022-.018-.019-.105-.035-.226-.149-.264-.157-.053-.324-.075-.508-.117l-.24-.005c.24-.169.452-.044.687.009-.063-.115-.153-.147-.23-.193-.082-.05-.17-.092-.25-.144-.06-.037-.12-.08-.072-.172zm10.233.325c-.23-.01-.427.08-.608.211-.034.026-.06.065-.105.117.087.026.15.046.232.065.044-.015.088-.03.13-.046.306-.114.61-.115.904.031.126.063.237.04.366-.005-.02-.031-.03-.054-.045-.071a.986.986 0 00-.448-.273c-.14-.044-.284-.024-.426-.03zM7.99 6.483a.308.308 0 00.002.133c.08.321.156.643.242.962.104.387.27.75.456 1.103.02.037.061.08.098.087a.404.404 0 00.253-.051l-.472-.84c-.23-.448-.405-.92-.579-1.394zM10.397.497c-.2-.008-.405.004-.603.034-.236.035-.47.087-.7.152-.287.08-.569.18-.852.273-.04.013-.074.038-.11.058.028.014.05.018.07.014.287-.068.58-.085.873-.09.134-.002.269.009.402.025.19.024.382.048.57.09.456.104.874.3 1.265.556.464.306.888.66 1.257 1.078.205.232.395.475.56.739.17.274.315.561.449.856.273.601.456 1.232.6 1.876.04.173.07.348.1.524.017.104.065.167.17.19.122.028.2.105.22.251-.003.102-.06.174-.129.24a1.065 1.065 0 00-.268.358.164.164 0 00.083-.039c.08-.086.162-.172.235-.265a.56.56 0 00.13-.333c.009-.05.022-.1.024-.15.007-.124-.017-.15-.143-.168-.025-.004-.049-.014-.073-.015-.082-.007-.125-.063-.137-.131-.033-.198-.004-.355.247-.408.086-.018.174-.03.26-.042.158-.023.315-.053.473-.067.14-.012.19.033.226.167.008.029.018.057.021.087.019.179-.008.225-.141.288-.027.013-.055.024-.078.042a.148.148 0 00-.051.067c-.039.144.073.382.206.445l.673.32c.023.011.05.015.075.023l.018-.026c-.015-.008-.032-.013-.044-.024a2.27 2.27 0 00-.544-.32 4.898 4.898 0 00-.173-.075.203.203 0 01-.126-.191c-.003-.085.045-.154.128-.187l.059-.025c.099-.044.118-.076.112-.187a.384.384 0 00-.008-.063c-.067-.294-.123-.59-.205-.88a9.478 9.478 0 00-.826-2.036 7.465 7.465 0 00-1.39-1.805 4.536 4.536 0 00-1.177-.824 3.656 3.656 0 00-1.016-.328 6.155 6.155 0 00-.712-.074zm6.719 5.955c.01.014.018.028.038.034l-.022-.044-.016.01zM4.103 3.917a.062.062 0 01-.03.012.455.455 0 01-.04.039c-.01.01-.02.02-.045.04l-.363.354c-.088.085-.17.178-.266.253-.284.22-.425.53-.544.855a.132.132 0 00-.007.071c.013.055.033.108.052.168l.074.026c-.017.056-.03.105-.047.152-.058.164-.118.327-.175.491-.005.015.008.036.019.077.08-.175.158-.33.225-.489.228-.544.484-1.074.819-1.561.09-.133.182-.266.283-.401.004-.006.007-.013.022-.03.001-.016.003-.032.015-.04l.008-.017zm12.976 2.408a.023.023 0 01.009.019.073.073 0 00-.006.01.188.188 0 00.007.02l.018.022c.002-.007.007-.016.005-.021-.003-.01-.012-.018-.02-.038a1.331 1.331 0 01-.013-.012zM4.199 4.48c-.003.004-.008.008-.027.014-.005.013-.011.025-.031.047a2.085 2.085 0 01-.124.167c-.048.07-.116.055-.181.041-.134-.028-.228.016-.287.143-.089.187-.187.37-.273.56-.049.108-.11.216-.118.36.081.003.154.007.228.008h.228a2.563 2.563 0 01-.079.264c-.01.052-.022.103-.033.155l.02.004c.018-.046.037-.092.067-.153.066-.142.13-.285.2-.426.02-.04.034-.1.116-.092 0 .043.004.084 0 .124-.005.045-.017.09-.028.143.141.043.086.174.115.269.102-.022.104-.195.248-.144v.205l.017.002.439-1.059c-.13 0-.246-.02-.358.033-.024.011-.058-.001-.108-.004.075-.15.139-.278.211-.417a.128.128 0 01.025-.036c0-.015-.001-.03.008-.038l.006-.02c-.005.006-.01.011-.028.017-.004.012-.009.024-.026.045a.085.085 0 01-.032.033c-.123.157-.09.164-.258.106-.079-.027-.078-.028-.047-.144.028-.046.056-.093.098-.15 0-.016-.001-.032.007-.042L4.2 4.48zm2.073-.67c-.003.006-.007.011-.027.016-.094.125-.194.246-.28.377-.155.238-.301.481-.451.723-.14.224-.345.368-.575.481-.017.008-.04.006-.079.011.012-.059.016-.109.033-.153a6.076 6.076 0 01.229-.518l-.007-.02a.138.138 0 01-.035.025c-.028.05-.055.1-.093.164-.26.424-.443.817-.442.95.024.004.048.011.073.013.177.013.188.007.26-.165.03-.07.077-.12.147-.15l.175-.07c.044-.018.085-.057.146-.032.003.05-.01.11.014.145.042.062.044.125.047.193.002.049.017.098.026.147.029-.034.039-.065.05-.097.142-.39.277-.782.428-1.17.1-.256.22-.504.33-.756.013-.03.013-.067.03-.092V3.81zm3.987-.34c0 .045.01.084.021.123.042.16.094.318.124.48.024.133.023.27.028.406 0 .033-.019.067-.032.11-.094-.058-.047-.158-.106-.215h-.125c-.015.072-.01.152-.046.2-.066.085-.155.154-.236.227-.043.038-.078.018-.103-.025l-.046-.087c-.065.035-.117.069-.172.093-.116.051-.235.095-.35.147-.085.038-.09.053-.07.147.014.075.034.148.047.223.013.072.05.109.123.124.233.05.462.115.657.265.058-.102.058-.102.168-.151.03-.014.06-.03.092-.042.08-.03.115-.017.15.06.023.048.041.098.066.158.06-.14-.042-.267.017-.416.157.18.24.39.375.567a.235.235 0 00.022-.098c.002-.124 0-.247.002-.371 0-.034.013-.067.02-.1l.032-.003c.11.155.13.354.226.52a3.036 3.036 0 00-.01-.392c-.004-.045 0-.074.05-.088.08.036.116.14.215.158-.03-.275-.423-1.137-.798-1.635-.114-.127-.2-.28-.34-.386zm-2.667.696c-.019.034-.03.05-.037.067-.061.185-.125.37-.18.556-.031.105-.087.169-.195.19-.09.019-.178.052-.268.073-.038.009-.089.015-.118-.003-.024-.016-.025-.069-.036-.106-.064.076-.082.087-.17.047-.133-.062-.262-.135-.393-.201-.048-.025-.093-.063-.17-.03-.043.12-.091.25-.137.382-.099.28-.087.242.095.453.046.048.102.03.154.023.054-.009.106-.03.16-.036.13-.013.26-.08.367-.015.204-.064.387-.122.571-.178.05-.015.089.005.114.054.022.042.034.093.082.121.038-.056-.013-.128.063-.178l.14.241-.042-1.46zm.278.358c-.096-.01-.107.01-.11.108-.002.038-.003.078.002.115.03.2.099.386.174.57.002.006.012.01.022.015l.078-.05c.052.036.081.088.153.088.205-.002.41.014.616.012.099-.001.158.042.205.12.018.03.024.077.088.066l-.08-.394c-.05-.195-.085-.395-.172-.589-.057.057-.114.068-.18.046a.72.72 0 00-.135-.028c-.22-.028-.44-.059-.66-.08zm10.254-1.727c.089.163.155.316.139.491-.016.168.026.342-.044.516-.047-.033-.088-.082-.112-.075-.117.035-.164-.057-.227-.115a4.772 4.772 0 01-.286-.29l-.104-.113a4.856 4.856 0 01-.023.019c.035.046.07.093.11.156.04.064.084.127.122.193.034.058.065.118.031.205-.082-.01-.164-.019-.246-.032-.06-.01-.101 0-.124.07-.031.098-.037.096-.15.09.02.042.036.08.057.116.041.074.03.138-.03.196-.06.06-.118.122-.178.181a.175.175 0 01-.185.046c-.222-.061-.447-.113-.67-.174-.032-.009-.063-.04-.086-.068-.03-.04-.052-.087-.08-.13-.044-.07-.09-.138-.136-.207a.18.18 0 00-.014.105c.012.127.03.253.035.38.005.1-.024.12-.121.104-.104-.017-.206-.04-.31-.058-.064-.012-.131-.028-.202.03l.081.208c.09 0 .166-.01.237.002a.819.819 0 01.458.251c.078.083.154.168.241.26l.018-.005c-.004-.006-.008-.013-.01-.04.014-.056-.062-.118.018-.178.031.03.064.057.088.09.058.078.111.159.169.257l.089.141.024-.013a2093.819 2093.819 0 01-.427-.934c.055.007.083.007.108.016.193.07.385.142.577.216.074.028.147.06.219.094.062.028.112.018.157-.033.05-.056.102-.112.154-.167.05-.051.095-.046.132.014.016.025.026.053.04.08.071.138.143.277.217.433l.159.308.025-.011c-.044-.106-.07-.218-.138-.334-.057-.182-.168-.346-.206-.545.136.034.362.326.567.732l.057.074.018-.011a1.563 1.563 0 01-.052-.127c-.046-.145-.097-.29-.136-.436-.022-.083-.036-.173.022-.26l.109.058-.026-.207.027-.016c.022.02.05.036.065.06.073.108.143.22.215.33.01.016.029.029.043.043-.036-.217-.2-.38-.229-.626l.155.112c.014-.166.012-.319.042-.465.032-.158-.023-.297-.063-.445.024.004.036.006.055.025.092.124.183.249.277.371.02.027.05.047.069.087l.04.063.019-.015a.293.293 0 01-.053-.082 27.922 27.922 0 01-.332-.49c-.221-.311-.363-.467-.485-.521zm-6.57.327c-.003.161.092.275.069.415l-.368.087c.09.139.032.237-.052.331-.05.057-.092.122-.143.178-.037.04-.046.078-.018.126l.16.275c.029.048.072.066.128.064.076-.003.152 0 .228-.001.116-.003.216.022.275.137.006.014.02.024.044.052.004-.059-.003-.098.01-.13.016-.04.04-.099.072-.108.084-.023.173-.024.26-.03.013-.001.027.018.04.029l.071.065c.019-.11-.082-.198-.024-.31l.126.04c-.026-.123-.07-.245-.071-.366 0-.123.051-.243.115-.36.107.062.16.156.234.253.183.265.36.533.494.834.165-.078.27.068.407.088-.003-.106-.133-.441-.197-.492a.142.142 0 00-.102-.028c-.06.011-.119.039-.191.063-.025-.039-.056-.078-.077-.122a3.936 3.936 0 00-.473-.783c-.076-.094-.16-.182-.228-.26l-.391.285c-.049.035-.094.03-.132-.017l-.169-.207c-.025-.03-.053-.059-.097-.108z"]};
function hostBadges(hosts = []) {
  const group = make("span", "p-hosts");
  if (!hosts.length) return make("span", "muted", "Host not recorded");
  for (const host of hosts) {
    const badge = make("span", `p-host p-host-${host}`);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    for (const d of hostMarks[host] || ["M4 4h16v16H4z"]) {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", d);
      svg.append(path);
    }
    badge.append(svg, make("span", "", hostNames[host] || host));
    group.append(badge);
  }
  return group;
}
let selectedStage = null;

document.getElementById("capture").textContent = `Captured ${data.generated_at} · on demand; continuous monitoring is off`;
for (const feature of data.features) {
  const option = make("option", "", `${feature.project ? feature.project + " · " : ""}${feature.archive_id ? "Archived · " : ""}${feature.id}${feature.workspace_key ? " · " + feature.workspace_key : ""}`);
  option.value = feature.identity;
  selector.append(option);
}
if (data.selected_feature) selector.value = data.selected_feature;

const when = iso => iso ? `${String(iso).slice(0, 16).replace("T", " ")} UTC` : "an unrecorded time";
const plural = (n, word) => `${n} ${n === 1 ? word : word.endsWith("y") ? word.slice(0, -1) + "ies" : word + "s"}`;
// Plain-language reasons the feature cannot move on, most urgent first.
function attention(feature) {
  const summary = feature.summary || {};
  const items = [];
  const add = (level, text, detail = "") => items.push({level, text, detail});
  const checks = feature.evidence.checks.status;
  const review = feature.evidence.review.status;
  const gate = feature.evidence.pr_ready.status;
  if (!feature.capture.stable && feature.capture.freshness === "unstable") add("bad", "Files changed while Pulse was reading them", "Regenerate the board once work pauses.");
  if (summary.pending_questions) add("bad", `${plural(summary.pending_questions, "question")} waiting for an answer`, "The workflow is paused on human input.");
  const failed = (summary.checks?.results || []).filter(r => r.required && r.status !== "pass").map(r => r.id);
  if (checks === "fail" || checks === "partial") add("bad", `Required checks failing: ${failed.join(", ") || "see latest run"}`, `Latest run ${when(summary.checks?.time)}.`);
  else if (checks === "stale") add("warn", "Check results are out of date", `They passed ${when(summary.checks?.time)}, but the spec, tasks or code changed afterwards, so they no longer prove the current work.`);
  else if (checks === "unavailable" && feature.lifecycle.stage === "implement") add("warn", "No required-check run recorded yet");
  const findings = summary.review?.blocking_findings || [];
  if (review === "fail") add("bad", `Review blocked${findings.length ? ` by ${plural(findings.length, "finding")}` : ""}`, findings[0] || "");
  else if (review === "stale") add("warn", "Independent review is out of date", `Review ${label(summary.review?.disposition)} ${when(summary.review?.time)} covered an earlier version of the work.`);
  if (gate === "fail") add("bad", "Local PR-ready gate failed against the current inputs");
  else if (gate === "stale") add("warn", "Local PR-ready gate ran against earlier inputs");
  else if (gate === "historical" && summary.gate?.last_result === "fail") add("warn", `Last PR-ready gate run failed${summary.gate.step ? ` at ${label(summary.gate.step)}` : ""}`, "That record is not bound to the current inputs, so rerun the gate after the checks.");
  const open = (summary.stories || []).filter(s => !s.done).length;
  if (open) add("warn", `${plural(open, "story")} not finished`);
  return items;
}

function renderWorkflow() {
  const feature = data.features.find(item => item.identity === selector.value);
  panel.replaceChildren();
  if (!feature) {
    panel.append(make("p", "p-empty", "No ADLC5 features were found in this workspace."));
    return;
  }
  const summary = feature.summary || {};
  const delivery = summary.delivery || {};
  const stage = feature.lifecycle.stage;
  const currentStatus = feature.evidence.pr_ready.status;
  const issues = attention(feature);
  selectedStage = stages.includes(selectedStage) ? selectedStage : stage;

  const heading = make("div", "heading");
  const titleGroup = make("div");
  titleGroup.append(make("div", "eyebrow", feature.archive_id ? `Archived feature · ${feature.archive_id}` : `Feature · ${feature.id}`));
  titleGroup.append(make("h1", "", summary.spec?.title || feature.id));
  if (summary.spec?.summary) titleGroup.append(make("p", "p-lede", summary.spec.summary));
  const chips = make("div", "p-chips");
  if (delivery.branch) chips.append(make("span", "p-chip", `Branch ${delivery.branch}${delivery.base ? " → " + delivery.base : ""}`));
  if (delivery.pr_url) {
    const pr = make("a", "p-chip", `Pull request · ${label(delivery.pr_status)}`);
    pr.href = delivery.pr_url; pr.target = "_blank"; pr.rel = "noopener noreferrer";
    chips.append(pr);
  } else if (delivery.branch) chips.append(make("span", "p-chip muted", "No pull request yet"));
  if (feature.hosts?.length) chips.append(hostBadges(feature.hosts));
  titleGroup.append(chips);
  const blocked = issues.some(item => item.level === "bad");
  const state = make("span", `status ${blocked ? "fail" : issues.length ? "warn" : ""}`, blocked ? "Blocked" : issues.length ? "Needs attention" : "On track");
  heading.append(titleGroup, state);
  panel.append(heading);

  const standHead = make("div", "p-panel-head");
  const stepText = feature.lifecycle.step ? `${label(stage)} · ${label(feature.lifecycle.step)}` : label(stage);
  standHead.append(make("h2", "", "Where it stands"), make("span", "sub", `Now at ${stepText}`));
  panel.append(standHead);
  const rail = make("div", "p-stages");
  rail.setAttribute("aria-label", "ADLC5 lifecycle stages");
  for (const [index, name] of stages.entries()) {
    const status = feature.lifecycle.stage_status?.[name] || "not recorded";
    const button = make("button", "p-stage");
    button.type = "button";
    button.dataset.status = status;
    button.setAttribute("aria-pressed", String(selectedStage === name));
    if (stage === name) button.setAttribute("aria-current", "step");
    button.append(make("span", "p-stage-name", `${String(index + 1).padStart(2, "0")} / ${name}`));
    button.append(make("span", "p-stage-state", label(status)));
    button.addEventListener("click", () => { selectedStage = name; renderWorkflow(); panel.querySelector('.p-stage[aria-pressed="true"]')?.focus(); });
    rail.append(button);
  }
  panel.append(rail);
  const substeps = Object.entries(delivery.substeps || {});
  if (stage === "implement" && substeps.length) {
    const row = make("div", "p-chips");
    for (const [name, status] of substeps) row.append(make("span", `p-chip ${statusClass(status)}`, `${label(name)} · ${label(status)}`));
    panel.append(row);
  }

  const next = make("div", "p-next");
  const nextCopy = make("div");
  nextCopy.append(make("div", "eyebrow", "Suggested next action"), make("strong", "", feature.next_action.label), make("small", "", `Because ${label(feature.next_action.reason_code)}`));
  next.append(nextCopy);
  panel.append(next);

  const attentionSection = make("section", "p-section");
  attentionSection.append(make("h2", "", issues.length ? "What needs attention" : "Nothing blocking"));
  const list = make("ul", "p-attention");
  for (const item of issues) {
    const li = make("li", `p-${item.level}`);
    li.append(make("strong", "", item.text));
    if (item.detail) li.append(make("span", "sub", item.detail));
    list.append(li);
  }
  if (!issues.length) list.append(make("li", "sub", "No failing, stale or missing evidence was recorded for this feature."));
  attentionSection.append(list);
  panel.append(attentionSection);

  const columns = make("div", "p-columns");
  const storySection = make("section");
  const stories = summary.stories || [];
  const storyHead = make("div", "p-panel-head");
  storyHead.append(make("h2", "", "Stories"), make("span", "sub", stories.length ? `${summary.stories_done} of ${stories.length} done` : "None recorded yet"));
  storySection.append(storyHead);
  if (stories.length) {
    const bar = make("div", "p-progress");
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${summary.stories_done} of ${stories.length} stories done`);
    const fill = make("span");
    fill.style = `width:${Math.round(100 * summary.stories_done / stories.length)}%`;
    bar.append(fill);
    storySection.append(bar);
    const storyList = make("ul", "p-stories");
    for (const story of stories) {
      const li = make("li");
      li.append(make("span", story.done ? "p-good" : "p-warn", story.done ? "✓" : "○"), make("span", "", `${story.id} · ${story.title}`), make("span", "sub", label(story.status)));
      storyList.append(li);
    }
    storySection.append(storyList);
  } else storySection.append(make("p", "sub", "Stories are written during the Tasks stage."));
  columns.append(storySection);

  const evidenceSection = make("section");
  const evidenceHead = make("div", "p-panel-head");
  evidenceHead.append(make("h2", "", "Checks and review"), make("span", "sub", `Checks ${label(feature.evidence.checks.status)} · review ${label(feature.evidence.review.status)}`));
  evidenceSection.append(evidenceHead);
  const results = summary.checks?.results || [];
  if (results.length) {
    const checkList = make("ul", "p-stories");
    for (const result of results) {
      const li = make("li");
      li.append(make("span", statusClass(result.status), result.status === "pass" ? "✓" : "✗"), make("span", "", `${label(result.id)}${result.required ? "" : " (optional)"}`), make("span", "sub", `${label(result.status)}${result.exit_code != null ? " · exit " + result.exit_code : ""}`));
      checkList.append(li);
    }
    evidenceSection.append(make("p", "sub", `Latest check run ${when(summary.checks.time)}`), checkList);
  } else evidenceSection.append(make("p", "sub", "No required-check run recorded."));
  const review = summary.review;
  if (review) {
    evidenceSection.append(make("h3", "p-subhead", `Independent review · ${label(review.disposition)} · ${when(review.time)}`));
    const notes = make("ul", "p-notes");
    for (const text of review.blocking_findings) notes.append(make("li", "p-bad", text));
    for (const text of review.notes) notes.append(make("li", "", text));
    if (!review.blocking_findings.length && !review.notes.length) notes.append(make("li", "sub", "No findings recorded."));
    evidenceSection.append(notes);
  }
  columns.append(evidenceSection);
  panel.append(columns);

  const checks = feature.evidence.checks;
  const usage = feature.usage;
  const evaluation = feature.evaluation || {};
  const percent = value => `${value.toFixed(1)}%`;
  const measured = [], unmeasured = [];
  const metric = (name, value, detail) => value == null ? unmeasured.push(name) : measured.push([name, value, detail]);
  metric("Known usage cost", typeof usage.known_cost_usd === "number" ? money(usage.known_cost_usd) : null, `${usage.accounted_records}/${usage.observed_records} records accounted · ${label(usage.status)}`);
  // Hook ledgers are often absent; transcripts of sessions matched to this feature still carry token counts.
  const worked = (data.fleet?.sessions || []).filter(session => sessionFeatures(session).includes(feature));
  const counted = worked.filter(s => typeof s.tokens === "number");
  const priced = counted.filter(s => typeof s.cost_usd === "number");
  metric("Agent tokens (transcripts)", counted.length ? `${(counted.reduce((n, s) => n + s.tokens, 0) / 1e6).toFixed(1)}M` : null,
    `${plural(counted.length, "session")} · whole-session totals, may include other work`);
  metric("Agent cost (transcripts)", priced.length ? money(priced.reduce((n, s) => n + s.cost_usd, 0)) : null,
    `${priced.length}/${counted.length} sessions priced${priced.length < counted.length ? " · rest use models missing from model-prices.yaml" : ""}`);
  metric("Outcome success", typeof evaluation.success_rate_pct === "number" ? percent(evaluation.success_rate_pct) : null, `${evaluation.successful || 0}/${evaluation.runs || 0} evaluated runs${evaluation.success_interval_pct ? ` · 95% Wilson interval ${evaluation.success_interval_pct.join("–")}%` : ""}`);
  metric("Projected cost savings", typeof evaluation.savings_pct === "number" ? percent(evaluation.savings_pct) : null, `Observed vs direct agent · ${evaluation.matched_cases} matched cases${evaluation.savings_range_pct ? ` · range ${evaluation.savings_range_pct.join("–")}%` : ""}`);
  metric("Escaped defects", evaluation.escaped_defects ?? null, "Recorded observation windows only");
  metric("Rework", evaluation.rework ?? null, "Recorded rework count");
  if (measured.length) {
    const metrics = make("div", "p-metrics");
    for (const [name, value, detail] of measured) {
      const tile = make("div", "p-metric");
      tile.append(make("label", "", name), make("strong", "p-value", String(value)), make("span", "sub", detail));
      metrics.append(tile);
    }
    panel.append(metrics);
  }
  if (unmeasured.length) panel.append(make("p", "sub p-unmeasured", `Not measured yet: ${unmeasured.join(", ")} · ${evaluation.reason || "no evaluation records"}`));

  if (worked.length) {
    const sessionHead = make("div", "p-panel-head p-section-gap");
    sessionHead.append(make("h2", "", "Agent sessions on this feature"), make("span", "sub", `${worked.length} recorded`));
    panel.append(sessionHead, sessionTable(worked.slice(0, 10)));
  }
  const sources = make("details", "p-sources");
  sources.append(make("summary", "", "Source records and provenance"));
  const rows = [
    ["Worktree", external(feature.workspace_label || "Not recorded", fileHref(feature.workspace_label, "."))],
    ["Spec", external(summary.spec?.source || "Not recorded", fileHref(feature.workspace_label, summary.spec?.source))],
    ["Checks", `${label(checks.status)} · ${checks.recorded_passed || 0} of ${checks.required || 0} required passed`],
    ["Local PR-ready gate", `${label(currentStatus)}${feature.evidence.pr_ready.reason ? " · " + feature.evidence.pr_ready.reason : ""} · remote CI and deployment are separate`],
    ["Input fingerprint", feature.capture.input_fingerprint || "unavailable"],
    ...results.filter(r => r.log).map(r => [`${label(r.id)} log`, r.log]),
  ];
  const table = make("table", "p-evidence");
  table.setAttribute("aria-label", "Evidence status and provenance");
  const body = make("tbody");
  for (const [name, value] of rows) {
    const tr = make("tr");
    const cell = make("td", "p-mono");
    cell.append(value instanceof Node ? value : document.createTextNode(value));
    tr.append(make("th", "", name), cell);
    body.append(tr);
  }
  table.append(body);
  sources.append(table);
  const selectedReceipts = feature.receipts.filter(item => !selectedStage || !item.stage || item.stage === selectedStage);
  const receipt = make("div", "p-receipt");
  receipt.append(make("strong", "", `${label(selectedStage)} receipts`));
  if (!selectedReceipts.length) receipt.append(make("span", "", "No recorded receipts for this stage."));
  for (const item of selectedReceipts) {
    const line = make("div", "", `${label(item.kind)} · ${label(item.status)} · `);
    line.append(external(item.id || "source unavailable", fileHref(feature.workspace_label, item.source)));
    receipt.append(line);
  }
  sources.append(receipt);
  const allEvents = [...feature.events].reverse().slice(0, 8);
  if (allEvents.length) {
    const eventList = make("ol", "p-events");
    for (const event of allEvents) {
      const item = make("li");
      const time = make("time", "", event.time ? event.time + " · " : "");
      time.append(external(event.id || "source unavailable", fileHref(feature.workspace_label, event.source)));
      item.append(make("span", "", `${label(event.kind)} · ${label(event.status)}${event.step ? " · " + label(event.step) : ""}`), time);
      eventList.append(item);
    }
    sources.append(make("h3", "p-subhead", `Latest ${allEvents.length} of ${feature.events.length} recorded events`), eventList);
  }
  if (feature.warnings?.length) sources.append(make("p", "p-warning muted", `Capture warnings · ${feature.warnings.join(" · ")}`));
  panel.append(sources);
}


const fleet = document.getElementById("fleet");
const nav = document.getElementById("navigation");
const external = (text, href) => {
  if (!href) return make("span", "", text);
  const node = make("a", "p-link", text);
  node.href = href;
  return node;
};
// "~/x" or "/x" worktree label + ".adlc5/f/file.jsonl:6" → file:// URL; null when the board has no home (shared snapshot).
function fileHref(workspaceLabel, relative) {
  const root = !workspaceLabel ? null : workspaceLabel.startsWith("~/") ? (data.home_uri ? data.home_uri + "/" + workspaceLabel.slice(2) : null) : workspaceLabel.startsWith("/") ? "file://" + workspaceLabel : null;
  return root && relative ? encodeURI(relative === "." ? root : root + "/" + String(relative).replace(/:\d+$/, "")) : null;
}
const sessionHref = s => s.host === "codex" && /^[0-9a-f-]{36}$/.test(s.id) ? "codex://threads/" + s.id : null;
const link = (text, route) => {
  const node = make("a", "p-link", text);
  node.href = "#" + route;
  return node;
};
for (const [name, route] of [["Projects", "projects"], ["Activity", "activity"], ["Settings", "settings"]]) nav.append(link(name, route));
selector.addEventListener("change", () => { location.hash = "workflow/" + encodeURIComponent(selector.value); });
function table(headings, rows) {
  const scroll = make("div", "p-table-scroll");
  const node = make("table");
  const header = make("tr");
  for (const name of headings) header.append(make("th", "", name));
  node.append(header);
  for (const row of rows) {
    const tr = make("tr");
    for (const value of row) {
      const td = make("td");
      td.append(value instanceof Node ? value : document.createTextNode(value ?? "Not recorded"));
      tr.append(td);
    }
    node.append(tr);
  }
  scroll.append(node);
  return scroll;
}
const workspaces = data.fleet?.workspace_inventory || [];
const projects = data.fleet?.projects || [];
const hostsFor = keys => [...new Set(workspaces.filter(w => keys.includes(w.key)).flatMap(w => w.hosts))];
const projectOfWorkspace = key => workspaces.find(w => w.key === key)?.project_id;
// A named feature matches in the session's own worktree first, then anywhere in the same project.
function sessionFeatures(session) {
  const named = data.features.filter(f => (session.features || []).includes(f.id) && !f.archive_id);
  const local = named.filter(f => (session.workspace_keys || []).includes(f.workspace_key));
  const projectIds = (session.workspace_keys || []).map(projectOfWorkspace);
  return local.length ? local : named.filter(f => projectIds.includes(f.project_id));
}
function featureStatus(feature) {
  const first = attention(feature)[0];
  return `${label(feature.lifecycle.step || feature.lifecycle.stage)} · ${first ? first.text : "on track"}`;
}
function sessionTable(rows) {
  return table(["Session", "Worktree", "Agent", "ADLC5 steps used", "Feature and its status now", "Last activity"], rows.map(s => {
    const features = sessionFeatures(s);
    const project = projectOfWorkspace(s.workspace_keys?.[0]);
    const title = make("div");
    title.append(features.length ? link(s.title || "Untitled session", "workflow/" + encodeURIComponent(features[0].identity)) : project ? link(s.title || "Untitled session", "project/" + project) : make("strong", "", s.title || "Untitled session"));
    const id = make("div", "sub");
    id.append(external(s.id, sessionHref(s)));
    title.append(id);
    const status = make("div");
    for (const f of features) status.append(link(f.id, "workflow/" + encodeURIComponent(f.identity)), make("div", "sub", featureStatus(f)));
    if (!features.length) status.append(make("span", "sub", (s.features || []).length ? `${s.features.join(", ")} · not found in scanned worktrees` : "No feature named in this session"));
    return [title, Object.values(s.workspace_labels || {}).join(", ") || s.project, hostBadges([s.host]), (s.actions || []).map(label).join(", ") || "ADLC5 mentioned only", status, s.last ? when(s.last) : "Not recorded"];
  }));
}
function showProjects() {
  fleet.append(make("h1", "", "Your projects"), make("p", "muted", "Applications first. Open a project to inspect its workflows and worktrees."));
  const cards = make("div", "p-projects");
  for (const project of projects) {
    const features = data.features.filter(f => f.project_id === project.id);
    const card = make("article", "p-project");
    card.append(link(project.name, "project/" + project.id), hostBadges(hostsFor(project.workspace_keys)));
    card.append(make("p", "muted", `${features.filter(f => !f.archive_id).length} active workflows · ${features.filter(f => f.archive_id).length} archived · ${project.workspace_keys.length} worktrees`));
    const blocked = features.filter(f => !f.archive_id && attention(f).some(item => item.level === "bad")).length;
    card.append(make("p", "", !features.length ? "No ADLC5 workflows yet" : blocked ? `${blocked} active workflows blocked` : "No active workflow is blocked"));
    const recent = (data.fleet?.sessions || []).filter(s => s.workspace_keys?.some(key => project.workspace_keys.includes(key))).map(s => s.last).filter(Boolean).sort().at(-1);
    card.append(make("small", "muted", "Last ADLC5 session: " + (recent || "Not recorded")));
    cards.append(card);
  }
  if (!projects.length) cards.append(make("p", "p-empty", "No projects found in the captured sources."));
  fleet.append(cards);
}
function showProject(id) {
  const project = projects.find(p => p.id === id);
  if (!project) return fleet.append(make("p", "p-empty", "Project not found in this snapshot."));
  fleet.append(link("Projects", "projects"), make("h1", "", project.name), hostBadges(hostsFor(project.workspace_keys)));
  const all = data.features.filter(f => f.project_id === id);
  fleet.append(make("h2", "", "Workflows"));
  if (!all.length) {
    fleet.append(make("p", "p-empty", "No ADLC5 workflows have been started in this project yet. Start one with /adlc5 in any of its worktrees; the sessions below only used ADLC5 commands."));
  } else {
    const filter = make("select");
    filter.setAttribute("aria-label", "Workflow archive filter");
    const active = all.filter(f => !f.archive_id).length;
    for (const [value, title] of [["active", `Active workflows (${active})`], ["archived", `Archived workflows (${all.length - active})`], ["all", `All workflows (${all.length})`]]) {
      const option = make("option", "", title); option.value = value; filter.append(option);
    }
    filter.value = active ? "active" : "all";
    const workflows = make("div");
    function list() {
      workflows.replaceChildren();
      const rows = all.filter(f => filter.value === "all" || Boolean(f.archive_id) === (filter.value === "archived"));
      workflows.append(table(["Workflow", "What it is", "Worktree", "Agents", "Status now", "Next action"], rows.map(f => [
        link(f.archive_id || f.id, "workflow/" + encodeURIComponent(f.identity)), f.summary?.spec?.title || "Not recorded", f.workspace_label, hostBadges(f.hosts), featureStatus(f), f.next_action.label])));
      if (!rows.length) workflows.append(make("p", "p-empty", "No workflows match this filter."));
    }
    filter.addEventListener("change", list); list();
    fleet.append(filter, workflows);
  }
  const sessions = (data.fleet?.sessions || []).filter(s => s.workspace_keys?.some(key => project.workspace_keys.includes(key)));
  fleet.append(make("h2", "", `Recent ADLC5 sessions (${Math.min(10, sessions.length)} of ${sessions.length})`));
  fleet.append(sessions.length ? sessionTable(sessions.slice(0, 10)) : make("p", "p-empty", "No ADLC5 sessions recorded for this project."));
  fleet.append(make("h2", "", "Worktrees"));
  fleet.append(table(["Worktree", "Recorded agents", "Settings"], workspaces.filter(w => w.project_id === id).map(w => [w.label, hostBadges(w.hosts), link("Settings for this worktree", "settings/worktree:" + w.key)])));
  fleet.append(link("Project settings", "settings/project:" + id));
}
function showActivity() {
  fleet.append(make("h1", "", "Activity"), make("p", "muted", "Agent sessions that used ADLC5, newest first. Open a session to jump to the feature it worked on. " + (data.fleet?.scope || "")));
  const kind = make("select"); kind.setAttribute("aria-label", "Activity type");
  for (const [value, title] of [["sessions", "Agent sessions"], ["attempts", "Runner attempts"]]) { const option = make("option", "", title); option.value = value; kind.append(option); }
  kind.value = "sessions";
  const search = make("input"); search.type = "search"; search.placeholder = "Search by title, project, feature or agent"; search.setAttribute("aria-label", "Search activity");
  const body = make("div"); let page = 0;
  function list() {
    body.replaceChildren();
    const rows = (data.fleet?.[kind.value] || []).filter(row => [row.title, row.project, row.feature, ...(row.features || []), row.id, row.host, hostNames[row.host]].join(" ").toLowerCase().includes(search.value.toLowerCase()));
    const visible = rows.slice(page * 25, page * 25 + 25);
    body.append(make("p", "muted", `${rows.length} records · page ${page + 1} of ${Math.max(1, Math.ceil(rows.length / 25))}`));
    body.append(kind.value === "sessions" ? sessionTable(visible)
      : table(["Project", "Feature", "Attempt", "Agent", "Worker status", "Model"], visible.map(a => {
        const feature = data.features.find(f => f.id === a.feature && f.project === a.project);
        return [a.project, feature ? link(a.feature, "workflow/" + encodeURIComponent(feature.identity)) : a.feature, a.id, hostBadges([a.host]), a.status, a.model];
      })));
    for (const [title, delta] of [["Previous", -1], ["Next", 1]]) {
      const button = make("button", "", title); button.disabled = page + delta < 0 || (page + delta) * 25 >= rows.length;
      button.addEventListener("click", () => { page += delta; list(); }); body.append(button);
    }
  }
  for (const node of [kind, search]) node.addEventListener(node === kind ? "change" : "input", () => { page = 0; list(); });
  fleet.append(kind, search, body); list();
}
const shellQuote = value => "'" + String(value).replaceAll("'", "'\\''") + "'";
// The board is a read-only file, so editing produces the exact CLI command that writes the chosen layer.
function changeControl(row, scope) {
  if (row.key.startsWith("installation.")) return make("span", "sub", "Set by the installer");
  const [kind, id] = scope.split(":");
  const workspace = kind === "worktree" ? workspaces.find(w => w.key === id)?.label : kind === "project" ? workspaces.find(w => w.project_id === id)?.label : null;
  const details = make("details", "p-change");
  details.append(make("summary", "", "Change"));
  const input = make("input");
  input.value = typeof row.value === "string" ? row.value : JSON.stringify(row.value);
  input.setAttribute("aria-label", "New value for " + row.key);
  const command = make("code", "p-mono");
  const copy = make("button", "", "Copy command");
  const update = () => { command.textContent = `adlc5 config set ${row.key} ${shellQuote(input.value)} --scope ${kind}${workspace ? " --workspace " + (workspace.startsWith("~/") ? "~/" + shellQuote(workspace.slice(2)) : shellQuote(workspace)) : ""}`; };
  update();
  input.addEventListener("input", update);
  copy.type = "button";
  copy.addEventListener("click", () => navigator.clipboard?.writeText(command.textContent).then(() => { copy.textContent = "Copied"; }));
  details.append(input, command, copy, make("div", "sub", `Writes the ${kind} layer, then regenerate the board.${row.status === "enforced" ? " An enforced machine value still wins." : ""}`));
  return details;
}
function showSettings(scope = "machine") {
  fleet.append(make("h1", "", "Settings"), make("p", "muted", "Effective configuration at capture time and where each value comes from. Use Change to get the command that writes a new value at this scope; explicit options override local defaults and enforced machine settings remain in force."));
  const selector = make("select"); selector.setAttribute("aria-label", "Settings scope");
  const scopes = data.settings?.scopes || {};
  const names = {machine: "Machine"};
  for (const p of projects) names["project:" + p.id] = "Project · " + p.name;
  for (const w of workspaces) names["worktree:" + w.key] = "Worktree · " + w.label;
  for (const key of Object.keys(scopes)) { const option = make("option", "", names[key] || key); option.value = key; selector.append(option); }
  selector.value = scopes[scope] ? scope : "machine";
  if (scope !== "machine" && !scopes[scope]) fleet.append(make("p", "p-warning", "Settings for this scope were not captured; showing machine settings."));
  selector.addEventListener("change", () => { location.hash = "settings/" + selector.value; }); fleet.append(selector);
  const settings = scopes[selector.value];
  if (!settings) return fleet.append(make("p", "p-empty", "Settings were not captured. Regenerate the board."));
  if (settings.error) fleet.append(make("p", "p-warning", settings.error));
  fleet.append(table(["Setting", "Effective value", "State", "Source", "Previous layers", ""], settings.rows.map(r => [r.key, JSON.stringify(r.value), r.status, r.source, r.history.map(h => `${h.layer}: ${JSON.stringify(h.value)}`).join(" → "), changeControl(r, selector.value)])));
  fleet.append(make("h2", "", "Configuration layers"), table(["Layer", "Source", "Available"], settings.layers.map(l => [l.layer, l.path, l.present ? "Yes" : "No"])));
  fleet.append(make("h2", "", "Storage"), table(["Purpose", "Location"], Object.entries(settings.storage)));
  fleet.append(make("h2", "", "Shared runtime"), table(["Property", "Value"], Object.entries(data.settings.shared_runtime || {})));
  fleet.append(make("h2", "", "Reporting and telemetry"), make("p", "", settings.telemetry), make("p", "muted", "Scan roots: " + data.settings.scan_roots.join(" · ")));
  fleet.append(make("h2", "", "Credential availability"), table(["Credential", "State"], Object.entries(settings.credentials)));
  fleet.append(make("h2", "", "Host integrations"), make("p", "muted", "Cached versions do not establish which plugin is active in an existing host process."));
  fleet.append(table(["Agent", "CLI on PATH", "Cached plugin versions", "Board runtime", "Observation"], data.settings.integrations.map(i => [hostBadges([i.host]), i.cli_available ? "Yes" : "No", i.cached_versions.join(", ") || "Not established", i.runtime_version, i.status])));
}
function route() {
  let parts;
  try { parts = location.hash.slice(1).split("/").map(decodeURIComponent); } catch { parts = ["projects"]; }
  const [view, id] = parts;
  panel.hidden = true; panel.replaceChildren(); fleet.hidden = false; fleet.replaceChildren();
  document.getElementById("workflow-picker").hidden = view !== "workflow";
  for (const item of nav.children) item.setAttribute("aria-current", item.href.endsWith("#" + (view === "project" || view === "workflow" ? "projects" : view || "projects")) ? "page" : "false");
  if (view === "workflow") {
    const feature = data.features.find(f => f.identity === id);
    if (!feature) return fleet.append(make("p", "p-empty", "Workflow not found in this snapshot."));
    fleet.append(link("Projects", "projects"), document.createTextNode(" / "), link(feature.project, "project/" + feature.project_id));
    selector.value = id; selectedStage = null; panel.hidden = false; renderWorkflow();
  } else if (view === "project") showProject(id);
  else if (view === "activity") showActivity();
  else if (view === "settings") showSettings(id);
  else showProjects();
  const heading = (panel.hidden ? fleet : panel).querySelector("h1");
  if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus({preventScroll: true}); }
  window.scrollTo?.(0, 0);
}
window.addEventListener("hashchange", route);
if (!location.hash && data.selected_feature) location.hash = "workflow/" + encodeURIComponent(data.selected_feature);
route();
