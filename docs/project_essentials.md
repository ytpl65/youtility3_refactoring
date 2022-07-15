## Add app names and model names at one place for better or collective view.   
   <br/>

### APP  PEOPLES 
- ####  MODELS 
  - People.
  - Pgroup. 
  - Pgbelonging. 
  - Capability. 
  - PeopleEventlog.

### APP  ONBOARDING 
- #### MODELS
  - Bt.
  - TypeAssist.
 
### APP  TENANTS 
- #### MODELS
  - Tenant. 
  - TenantAwareModel.


## DEVELOPMENT BEST PRACTICES FOR BETTER COLLABORATION

```diff
! NOTE: Following practices are written in articles of experienced django professionals and most recommended in every django project.* 
```

- > Model/Form/ANY Class Names should be "PascalCased". 
- > Function or method Names should be "snake_cased". 
- > Variable Names should be "snake_cased".
- > Grid-View template-names should be <template_name_list>.html.
- > Form-View template-names should be <template_name_form>.html.
- > For CSS & JS follow the same above shown pattern.
- > Function should have only one return statement.
- > Size of function body should be of maximum visible screen_length.
- > Order of importing libraries should be as follows:
  - 1.python standard libraries.
  - 2.django core libraries.
  - 3.third-party django/python packages.
  - 4.project-level.

<br/>

## Deciding class based view or function based view
<img src="https://miro.medium.com/max/1050/1*1NgVsYmmLCiwXUy-uE0VLA.jpeg"
     alt="Markdown Monster icon"
     style="width:720px; height:520px" />