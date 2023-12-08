document.addEventListener("DOMContentLoaded", function ()
{
  var urlParams = new URLSearchParams(window.location.search);
  var page_obj = urlParams.get('page');
  if (page_obj < 1)
  {
    page_obj=1;
  }

  var userRows = document.querySelectorAll("#userTable tbody tr");
  userRows.forEach(function (row, index)
  {
    var userNumberCell = row.querySelector(".user-number");
    userNumberCell.textContent = index + 1 + (page_obj - 1) * 10;
  });
});

function toggleSecret() {
   var secretDiv = document.getElementById("secret");
   if (secretDiv.style.display === "none") {
      secretDiv.style.display = "block";
   } else {
      secretDiv.style.display = "none";
   }
}
