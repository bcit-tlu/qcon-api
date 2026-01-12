-- Replace HTML <br> tags with proper pandoc LineBreak nodes
return {
  RawInline = function(el)
    if el.format:match("html") then
      local text = el.text:lower()
      if text == "<br>" or text == "<br/>" or text == "<br />" then
        return pandoc.LineBreak()
      end
    end
  end
}
