const {request, uploadPhoto, requireLogin, fail} = require('../../utils/api')
Page({
  data:{imagePath:'',image:'',text:'',tag:'待归类',source:'本人手写整理',busy:false,result:null},
  onShow(){requireLogin()},
  setText(e){this.setData({text:e.detail.value})},
  setTag(e){this.setData({tag:e.detail.value})},
  setSource(e){this.setData({source:e.detail.value})},
  async choose(){
    try {
      const res=await wx.chooseMedia({count:1,mediaType:['image'],sourceType:['camera','album'],sizeType:['compressed']})
      const path=res.tempFiles[0].tempFilePath
      this.setData({imagePath:path,busy:true,result:null})
      const result=await uploadPhoto(path)
      this.setData({image:result.image,text:result.text||''})
      if(!result.ocr_ok) wx.showModal({title:'识别未完成',content:'本机 OCR 未就绪，请手动输入或修正题目文字。',showCancel:false})
    }catch(e){fail(e)}finally{this.setData({busy:false})}
  },
  async save(){
    if(this.data.busy) return
    if(this.data.text.trim().length<2)return wx.showToast({title:'请填写题目文字',icon:'none'})
    this.setData({busy:true})
    try {
      const res=await request('POST','/questions',{
        text:this.data.text,tag:this.data.tag||'待归类',source:this.data.source||'本人手写整理',image:this.data.image
      })
      this.setData({result:res,image:'',imagePath:'',text:''})
      wx.showToast({title:'已存入我的错题',icon:'success'})
    }catch(e){fail(e)}finally{this.setData({busy:false})}
  }
})
