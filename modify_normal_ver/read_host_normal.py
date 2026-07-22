/*
 게시글 수정(일반에디터)
*/

function runModifyNormal(sheet) {

  // 로그인 정보
  var userId = "circus2354";
  var userPw = "m0derni@2357";

  // 수정 페이지 링크(C3)
  var modifyUrl = sheet.getRange("M3").getValue().toString().trim();

  // 일반 에디터에 넣을 내용(I5)
  var text = sheet.getRange("M4").getValue().toString();

  // URL이 없으면 종료
  if (!modifyUrl) return;

  var payload = {
    id: userId,
    pw: userPw,
    url: modifyUrl,
    text: text
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = UrlFetchApp.fetch(
    "http://64.176.232.213:5000/modify-normal",
    options
  );

  var result = JSON.parse(response.getContentText());

  if (result.success) {

    sheet.getRange("M7").setValue("완료");

  } else {

    sheet.getRange("M7").setValue(
      "실패 : " + result.message
    );

  }

}
